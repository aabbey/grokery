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
from app.models import UserCurrentRecipes, UserGroceryList

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
def get_grocery_list(request):
    try:
        # Get the user's grocery list
        grocery_list = UserGroceryList.objects.get(user=request.user).items
        
        # Render the grocery list template
        html = render_to_string('grocery_list_expanded.html', {
            'grocery_items': grocery_list
        })
        
        return JsonResponse({
            'status': 'success',
            'html': html
        })
    except UserGroceryList.DoesNotExist:
        return JsonResponse({
            'status': 'success',
            'html': render_to_string('grocery_list_expanded.html', {
                'grocery_items': []
            })
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@login_required(login_url='account_login')
async def stream_recipe_generation(request):
    async def event_stream():
        try:
            # Stage 1: Get recipe templates
            logger.info("Starting recipe template generation")
            recipe_templates = await RecipeService.get_recipe_templates()
            logger.info(f"Generated {len(recipe_templates)} recipe templates")
            
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
                            logger.info(f"Generated image for recipe {image_match}")
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
                            logger.info(f"Generated details for recipe {detail_match}")
                            
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
                        logger.info("All recipe details complete, generating grocery list")
                        grocery_list = await RecipeService.generate_grocery_list(completed_details)
                        logger.info(f"Generated grocery list with {len(grocery_list)} items")
                        
                        # Save recipes and grocery list to database
                        logger.info("Saving recipes to database")
                        # Include images in the saved recipes
                        recipes_to_save = []
                        for recipe in recipes:
                            recipes_to_save.append({
                                'id': recipe['id'],
                                'title': recipe['title'],
                                'description': recipe['description'],
                                'visual_description': recipe['visual_description'],
                                'ingredients': recipe['ingredients'],
                                'instructions': recipe['instructions'],
                                'image': recipe['image']
                            })
                        
                        recipes_obj, created = await sync_to_async(UserCurrentRecipes.objects.update_or_create)(
                            user=request.user,
                            defaults={'recipes': recipes_to_save}
                        )
                        logger.info(f"{'Created' if created else 'Updated'} recipes in database")
                        
                        logger.info("Saving grocery list to database")
                        grocery_obj, created = await sync_to_async(UserGroceryList.objects.update_or_create)(
                            user=request.user,
                            defaults={'items': grocery_list}
                        )
                        logger.info(f"{'Created' if created else 'Updated'} grocery list in database")
                        
                        yield "data: " + json.dumps({
                            "type": "grocery_list",
                            "grocery_list": grocery_list
                        }) + "\n\n"
                        await asyncio.sleep(0)
                    except Exception as e:
                        logger.error(f"Error generating/saving grocery list: {str(e)}\n{traceback.format_exc()}")
            
            # Send completion message
            logger.info("Recipe generation complete")
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