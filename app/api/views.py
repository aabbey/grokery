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
        try:
            print("\n=== Starting Recipe Stream Event Loop ===")
            logger.info("Starting recipe stream")
            
            # 1) Fetch recipe templates
            print("1. Fetching recipe templates...")
            recipe_templates = await RecipeService.get_recipe_templates()
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

            # 2) Get full details and image tasks in parallel
            print("\n=== Starting Parallel Recipe Detail Fetching ===")
            logger.info("Starting parallel recipe detail fetching")
            detail_tasks = []
            for template in recipe_templates:
                print(f"   Creating detail task for recipe: {template['title']}")
                detail_tasks.append(RecipeService.get_recipe_details(template))

            print(f"\n4. Waiting for {len(detail_tasks)} recipe details to complete...")
            # Wait for all recipe details to complete
            detail_results = await asyncio.gather(*detail_tasks, return_exceptions=True)
            print("   ✓ All recipe details fetched")
            logger.info("Completed fetching recipe details")

            # Process recipe details and collect image tasks
            print("\n=== Processing Recipe Details & Images ===")
            image_tasks = []
            updated_recipes = []
            
            for template, result in zip(recipe_templates, detail_results):
                if isinstance(result, Exception):
                    print(f"   ✗ Failed to get details for recipe {template['title']}: {str(result)}")
                    logger.error(f"Failed to get details for recipe {template['title']}: {str(result)}")
                    processed_recipes.add(template['id'])  # Mark as processed even if failed
                    continue

                if result is None or not isinstance(result, tuple) or len(result) != 2:
                    print(f"   ✗ Invalid result for recipe {template['title']}")
                    logger.warning(f"Invalid result for recipe {template['title']}")
                    processed_recipes.add(template['id'])  # Mark as processed even if invalid
                    continue

                recipe_data, img_task = result
                if not recipe_data or 'id' not in recipe_data:
                    print(f"   ✗ Invalid recipe data for {template['title']}")
                    logger.warning(f"Invalid recipe data for {template['title']}")
                    processed_recipes.add(template['id'])  # Mark as processed even if invalid
                    continue

                rid = recipe_data['id']
                if rid in recipes_by_id:
                    print(f"   Processing details for recipe: {recipe_data['title']}")
                    logger.info(f"Processing details for recipe {recipe_data['title']}")
                    recipes_by_id[rid].update({
                        'ingredients': recipe_data.get('ingredients', []),
                        'instructions': recipe_data.get('instructions', [])
                    })
                    updated_recipes.append(recipes_by_id[rid])
                    if img_task:
                        print(f"   + Added image task for recipe: {recipe_data['title']}")
                        logger.info(f"Added image task for recipe {recipe_data['title']}")
                        image_tasks.append((rid, img_task))

            # Yield recipe details update
            if updated_recipes:
                print(f"\n5. Sending {len(updated_recipes)} recipe details to client...")
                logger.info(f"Sending {len(updated_recipes)} recipe details updates")
                yield "data: " + json.dumps({"recipes": updated_recipes}) + "\n\n"
                print("   ✓ Recipe details sent")

            # 3) Process images as they complete
            if image_tasks:
                print(f"\n=== Processing {len(image_tasks)} Image Tasks ===")
                logger.info(f"Processing {len(image_tasks)} image tasks")
                pending = set(image_tasks)
                while pending:
                    print(f"\n6. Waiting for next image... ({len(pending)} remaining)")
                    try:
                        done, pending_set = await asyncio.wait(
                            [task for _, task in pending],
                            return_when=asyncio.FIRST_COMPLETED,
                            timeout=30
                        )
                        
                        # Update pending set before processing to avoid race conditions
                        pending = {(rid, task) for rid, task in pending if task not in done}
                        
                        # Process completed images
                        updated_recipes = []
                        for task in done:
                            try:
                                # Find the corresponding recipe_id
                                recipe_id = next(rid for rid, t in image_tasks if t == task)
                                try:
                                    print(f"   Processing image for recipe ID: {recipe_id}")
                                    logger.info(f"Processing completed image task for recipe {recipe_id}")
                                    image_data = await asyncio.wait_for(task, timeout=5.0)
                                    if recipe_id in recipes_by_id:
                                        recipe = recipes_by_id[recipe_id]
                                        if image_data:
                                            print(f"   Optimizing image for: {recipe['title']}")
                                            logger.info(f"Optimizing image for recipe {recipe['title']}")
                                            optimized_image = RecipeService._decode_and_optimize_image(image_data)
                                            recipe['image'] = optimized_image
                                        recipe['image_loading'] = False
                                        updated_recipes.append(recipe)
                                        processed_recipes.add(recipe_id)  # Mark recipe as fully processed
                                        print(f"   ✓ Successfully updated image for: {recipe['title']}")
                                        logger.info(f"Successfully updated image for recipe {recipe['title']}")
                                except asyncio.TimeoutError:
                                    print(f"   ✗ Timeout processing image for recipe {recipe_id}")
                                    logger.error(f"Timeout processing image for recipe {recipe_id}")
                                    if recipe_id in recipes_by_id:
                                        recipe = recipes_by_id[recipe_id]
                                        recipe['image'] = None
                                        recipe['image_loading'] = False
                                        updated_recipes.append(recipe)
                                        processed_recipes.add(recipe_id)  # Mark as processed even if timeout
                            except Exception as e:
                                print(f"   ✗ Error processing image task: {str(e)}")
                                logger.error(f"Error processing image task: {str(e)}")
                                continue

                        # Yield the updated recipes for the front-end
                        if updated_recipes:
                            print(f"\n7. Sending {len(updated_recipes)} recipe image updates to client...")
                            logger.info(f"Sending {len(updated_recipes)} recipe image updates")
                            yield "data: " + json.dumps({"recipes": updated_recipes}) + "\n\n"
                            print("   ✓ Image updates sent")

                    except asyncio.TimeoutError:
                        # Handle timeout by marking remaining recipes as failed
                        print("\n   ✗ Timeout waiting for image tasks")
                        logger.warning("Timeout waiting for image tasks")
                        updated_recipes = []
                        for rid, task in pending:
                            if rid in recipes_by_id:
                                recipe = recipes_by_id[rid]
                                recipe['image'] = None
                                recipe['image_loading'] = False
                                updated_recipes.append(recipe)
                                processed_recipes.add(rid)  # Mark as processed even if timeout
                                print(f"   Marking recipe {recipe['title']} as failed due to timeout")
                        if updated_recipes:
                            print(f"\n8. Sending {len(updated_recipes)} failed image updates due to timeout...")
                            logger.info(f"Sending {len(updated_recipes)} failed image updates due to timeout")
                            yield "data: " + json.dumps({"recipes": updated_recipes}) + "\n\n"
                            print("   ✓ Failed updates sent")
                        break

            # Only complete the stream when all recipes have been processed
            if len(processed_recipes) == total_recipes:
                print("\n=== Recipe Stream Completed ===")
                logger.info("Recipe stream completed successfully")
                yield "data: " + json.dumps({"done": True}) + "\n\n"
                print("✓ Final completion message sent")
            else:
                print(f"\n✗ Stream incomplete: Processed {len(processed_recipes)}/{total_recipes} recipes")
                logger.error(f"Stream incomplete: Only processed {len(processed_recipes)}/{total_recipes} recipes")
                yield "data: " + json.dumps({'error': 'Not all recipes were processed'}) + "\n\n"

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
        print("\n=== Starting Iterator Event Loop ===")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            print("1. Creating async generator...")
            agen = event_stream_async()
            while True:
                try:
                    print("2. Waiting for next async item...")
                    yield loop.run_until_complete(agen.__anext__())
                    print("   ✓ Item yielded to client")
                except StopAsyncIteration:
                    print("3. Async generator completed")
                    break
        finally:
            print("4. Closing event loop")
            loop.close()
            print("=== Iterator Complete ===\n")

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