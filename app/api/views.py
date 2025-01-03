from django.http import JsonResponse, StreamingHttpResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.core.serializers.json import DjangoJSONEncoder
from asgiref.sync import sync_to_async, async_to_sync
import asyncio
import json
import logging
import traceback

from app.services.recipe_service import RecipeService
from app.services.grocery_service import GroceryService

logger = logging.getLogger(__name__)


@login_required(login_url='account_login')
@require_http_methods(["DELETE"])
def remove_grocery_item(request, item_id):
    try:
        success = GroceryService.remove_item(item_id, request.user)
        if success:
            return JsonResponse({
                'status': 'success',
                'message': f'Item {item_id} removed successfully'
            })
        raise Exception("Failed to remove item")
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@login_required(login_url='account_login')
def get_grocery_item_details(request, item_id):
    try:
        item_details = GroceryService.get_item_details(item_id)
        html = render_to_string('grocery_item_details.html', {
            'item': item_details
        })
        
        return JsonResponse({
            'status': 'success',
            'html': html
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@login_required(login_url='account_login')
async def get_simulated_recipe_data(request):
    async def generate_response():
        try:
            # Stage 1: Get recipe templates
            recipe_templates = await RecipeService.get_recipe_templates()
            logger.info("Recipe templates generated successfully")
            
            yield json.dumps({
                'status': 'templates',
                'recipes': recipe_templates,
                'grocery_list': []
            }, cls=DjangoJSONEncoder) + '\n'
            
            # Stage 2: Get detailed recipes
            try:
                detailed_recipes = await RecipeService.get_all_recipe_details(recipe_templates)
                logger.info("Detailed recipes generated successfully")
                
                yield json.dumps({
                    'status': 'details',
                    'recipes': detailed_recipes,
                    'grocery_list': []
                }, cls=DjangoJSONEncoder) + '\n'
            except Exception as e:
                logger.error(f"Error generating detailed recipes: {str(e)}\n{traceback.format_exc()}")
                yield json.dumps({
                    'status': 'error',
                    'message': 'Error generating detailed recipes'
                }) + '\n'
                return
            
            # Stage 3: Generate grocery list
            try:
                grocery_list = await RecipeService.generate_grocery_list(detailed_recipes)
                logger.info("Grocery list generated successfully")
                
                yield json.dumps({
                    'status': 'complete',
                    'recipes': detailed_recipes,
                    'grocery_list': grocery_list
                }, cls=DjangoJSONEncoder) + '\n'
            except Exception as e:
                logger.error(f"Error generating grocery list: {str(e)}\n{traceback.format_exc()}")
                yield json.dumps({
                    'status': 'error',
                    'message': 'Error generating grocery list'
                }) + '\n'
                
        except Exception as e:
            logger.error(f"Error in recipe data generation: {str(e)}\n{traceback.format_exc()}")
            yield json.dumps({
                'status': 'error',
                'message': 'Error generating recipe data'
            }) + '\n'

    # Convert async generator to sync iterator for StreamingHttpResponse
    async def async_iter():
        async for chunk in generate_response():
            yield chunk

    return StreamingHttpResponse(
        streaming_content=async_iter(),
        content_type='application/x-ndjson'
    )

@login_required(login_url='account_login')
async def stream_recipe_generation(request):
    async def event_stream():
        try:
            # Stage 1: Get recipe templates
            logger.info("Starting recipe template generation")
            recipe_templates = await RecipeService.get_recipe_templates()
            
            # Send initial templates to frontend
            recipes = [{
                **template,
                'image': None,
                'image_loading': True,
                'ingredients': [],
                'instructions': []
            } for template in recipe_templates]
            
            yield "data: " + json.dumps({
                "type": "templates",
                "recipes": recipes
            }) + "\n\n"
            await asyncio.sleep(0)  # Allow the event to be sent immediately
            
            # Stage 2: Start image generation and recipe details in parallel
            image_tasks = []
            detail_tasks = []
            
            # Create tasks for both operations
            for template in recipe_templates:
                # Start image generation
                recipe_text = f"{template['title']} - {template['description']}"
                image_task = asyncio.create_task(
                    RecipeService._generate_recipe_image(recipe_text, template['visual_description'])
                )
                image_tasks.append((template['id'], image_task))
                
                # Start recipe details
                detail_task = asyncio.create_task(
                    RecipeService.get_recipe_details(template)
                )
                detail_tasks.append((template['id'], detail_task))
            
            # Create a map for easy recipe lookup
            recipes_by_id = {r['id']: r for r in recipes}
            all_tasks = [task for _, task in image_tasks + detail_tasks]
            completed_details = []
            
            # Process tasks as they complete
            while all_tasks:
                done, pending = await asyncio.wait(
                    all_tasks,
                    return_when=asyncio.FIRST_COMPLETED
                )
                all_tasks = list(pending)
                
                # Process completed tasks
                updates = []
                for task in done:
                    try:
                        result = await task
                        
                        # Check if this was an image task
                        image_match = next((rid for rid, t in image_tasks if t == task), None)
                        if image_match is not None:
                            recipe = recipes_by_id[image_match]
                            if result:
                                recipe['image'] = RecipeService._decode_and_optimize_image(result)
                            recipe['image_loading'] = False
                            updates.append(recipe)
                            continue
                            
                        # Must be a recipe details task
                        detail_match = next((rid for rid, t in detail_tasks if t == task), None)
                        if detail_match is not None and result:
                            recipe = recipes_by_id[detail_match]
                            recipe.update({
                                'ingredients': result['ingredients'],
                                'instructions': result['instructions']
                            })
                            updates.append(recipe)
                            completed_details.append(result)
                            
                    except Exception as e:
                        logger.error(f"Error processing task: {str(e)}")
                        continue
                
                # Send any updates to frontend
                if updates:
                    yield "data: " + json.dumps({
                        "type": "updates",
                        "recipes": updates
                    }) + "\n\n"
                    await asyncio.sleep(0)  # Allow the event to be sent immediately
                
                # If all recipe details are complete, generate grocery list
                if len(completed_details) == len(recipe_templates) and not any(t for rid, t in detail_tasks if not t.done()):
                    try:
                        grocery_list = await RecipeService.generate_grocery_list(completed_details)
                        yield "data: " + json.dumps({
                            "type": "grocery_list",
                            "grocery_list": grocery_list
                        }) + "\n\n"
                        await asyncio.sleep(0)  # Allow the event to be sent immediately
                    except Exception as e:
                        logger.error(f"Error generating grocery list: {str(e)}")
            
            # Send completion message
            yield "data: " + json.dumps({"type": "complete"}) + "\n\n"
            
        except Exception as e:
            logger.error(f"Error in recipe generation stream: {str(e)}\n{traceback.format_exc()}")
            yield "data: " + json.dumps({
                "type": "error",
                "error": str(e)
            }) + "\n\n"

    return StreamingHttpResponse(
        streaming_content=event_stream(),
        content_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    ) 