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
async def get_recipes(request):
    try:
        # Get just the recipe templates without details
        recipe_templates = await RecipeService.get_recipe_templates()
        
        # Add loading state to each recipe
        recipes = [{
            **template,
            'image': None,
            'image_loading': True,
            'ingredients': [],
            'instructions': []
        } for template in recipe_templates]
        
        return JsonResponse({
            'status': 'success',
            'recipes': recipes
        })
    except Exception as e:
        logger.error(f"Error getting recipes: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'status': 'error',
            'message': 'Error generating recipes'
        }, status=400)

@login_required(login_url='account_login')
def stream_recipe_updates(request):
    async def event_stream_async():
        image_tasks = []  # Initialize at the start
        try:
            print("\n=== Starting Recipe Stream Event Loop ===")
            logger.info("Starting recipe stream")
            
            # 1) Fetch recipe templates
            print("1. Fetching recipe templates...")
            recipe_templates = await RecipeService.get_recipe_templates()
            if not recipe_templates:
                raise ValueError("Failed to get recipe templates")
            print(f"   ✓ Fetched {len(recipe_templates)} recipe templates")
            logger.info(f"Fetched {len(recipe_templates)} recipe templates")
            
            # Track the total number of recipes we expect to process
            total_recipes = len(recipe_templates)
            processed_recipes = set()
            
            # Convert them into partial recipes (with image_loading=True, etc.)
            print("2. Converting templates to partial recipes...")
            recipes = [{
                **template,
                'image': None,
                'image_loading': True,
                'ingredients': [],
                'instructions': []
            } for template in recipe_templates]
            print(f"   ✓ Created {len(recipes)} partial recipes")

            # Make a quick lookup by id
            recipes_by_id = {r['id']: r for r in recipes}

            # Immediately yield the initial recipes (templates only)
            print("3. Yielding initial templates to client...")
            logger.info("Sending initial recipe templates")
            yield "data: " + json.dumps({"recipes": recipes}) + "\n\n"
            print("   ✓ Initial templates sent")

            # Start both image generation and recipe details in parallel
            print("\n=== Starting Parallel Processing ===")
            
            # Create tasks list for all async operations
            tasks = []
            
            # Start image generation tasks
            print("4. Starting image generation tasks...")
            for template in recipe_templates:
                recipe_text = f"{template['title']} - {template['description']}"
                print(f"   Starting image task for: {template['title']}")
                image_task = asyncio.create_task(
                    RecipeService._generate_recipe_image(recipe_text, template['visual_description'])
                )
                image_tasks.append((template['id'], image_task))
                tasks.append(image_task)
            print(f"   ✓ Started {len(image_tasks)} image generation tasks")

            # Start recipe detail tasks
            print("5. Starting recipe detail tasks...")
            detail_tasks = []
            for template in recipe_templates:
                print(f"   Creating detail task for recipe: {template['title']}")
                detail_task = asyncio.create_task(RecipeService.get_recipe_details(template))
                detail_tasks.append((template['id'], detail_task))
                tasks.append(detail_task)
            print(f"   ✓ Created {len(detail_tasks)} recipe detail tasks")

            # Process tasks as they complete
            print("\n6. Processing tasks as they complete...")
            while tasks:
                done, pending = await asyncio.wait(
                    tasks,
                    return_when=asyncio.FIRST_COMPLETED
                )
                tasks = list(pending)

                # Process completed tasks
                updated_recipes = []
                for task in done:
                    try:
                        result = await task
                        
                        # Find which task this was
                        image_task = next((rid for rid, t in image_tasks if t == task), None)
                        detail_task = next((rid for rid, t in detail_tasks if t == task), None)
                        
                        if image_task is not None:
                            # This was an image task
                            rid = image_task
                            if rid in recipes_by_id:
                                recipe = recipes_by_id[rid]
                                if result:
                                    print(f"   Optimizing image for: {recipe['title']}")
                                    optimized_image = RecipeService._decode_and_optimize_image(result)
                                    recipe['image'] = optimized_image
                                    print(f"   ✓ Image optimized for: {recipe['title']}")
                                else:
                                    print(f"   ✗ No image data received for: {recipe['title']}")
                                recipe['image_loading'] = False
                                updated_recipes.append(recipe)
                                print(f"   ✓ Successfully updated image for: {recipe['title']}")
                        
                        elif detail_task is not None:
                            # This was a recipe details task
                            rid = detail_task
                            if result and rid in recipes_by_id:
                                recipe = recipes_by_id[rid]
                                recipe.update({
                                    'ingredients': result.get('ingredients', []),
                                    'instructions': result.get('instructions', [])
                                })
                                updated_recipes.append(recipe)
                                processed_recipes.add(rid)
                                print(f"   ✓ Successfully updated recipe details: {recipe['title']}")
                    
                    except Exception as e:
                        print(f"   ✗ Error processing task: {str(e)}")
                        logger.error(f"Error processing task: {str(e)}")
                        continue

                # Send updates if we have any
                if updated_recipes:
                    print(f"   Sending {len(updated_recipes)} recipe updates to client...")
                    yield "data: " + json.dumps({"recipes": updated_recipes}) + "\n\n"
                    print("   ✓ Updates sent")

            # Send completion message
            print("\n=== Recipe Stream Completed ===")
            logger.info("Recipe stream completed successfully")
            yield "data: " + json.dumps({"done": True}) + "\n\n"
            print("✓ Final completion message sent")

        except Exception as e:
            print(f"\n✗ Error in recipe stream: {str(e)}")
            logger.error(f"Error in recipe stream: {str(e)}\n{traceback.format_exc()}")
            yield "data: " + json.dumps({'error': str(e)}) + "\n\n"
        finally:
            # Clean up any remaining tasks
            for _, task in image_tasks:
                if not task.done():
                    print(f"Cancelling unfinished image task")
                    task.cancel()
            print("\n=== Stream Cleanup Complete ===\n")

    def iterator():
        """Convert async generator to sync iterator."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        agen = event_stream_async()
        try:
            while True:
                try:
                    yield loop.run_until_complete(agen.__anext__())
                except StopAsyncIteration:
                    break
        finally:
            loop.close()

    return StreamingHttpResponse(
        streaming_content=iterator(),
        content_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )

@login_required(login_url='account_login')
async def get_grocery_list(request):
    try:
        # Get templates first (needed for grocery list generation)
        recipe_templates = await RecipeService.get_recipe_templates()
        # Get details for grocery list
        detailed_recipes = await RecipeService.get_all_recipe_details(recipe_templates)
        # Generate grocery list
        grocery_list = await RecipeService.generate_grocery_list(detailed_recipes)
        
        return JsonResponse({
            'status': 'success',
            'grocery_list': grocery_list
        })
    except Exception as e:
        logger.error(f"Error getting grocery list: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'status': 'error',
            'message': 'Error generating grocery list'
        }, status=400)

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