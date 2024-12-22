from django.http import JsonResponse, StreamingHttpResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.core.serializers.json import DjangoJSONEncoder
from asgiref.sync import sync_to_async
import asyncio
import json
import logging
import traceback

from app.services.recipe_service import RecipeService
from app.services.grocery_service import GroceryService

logger = logging.getLogger(__name__)

@login_required(login_url='account_login')
def get_grocery_list(request):
    context = {
        'debug': 'This is a test response'
    }
    html = render_to_string('grocery_list_expanded.html', context)
    return JsonResponse({'html': html})

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
            # Stage 1: Get recipe templates (convert sync to async)
            recipe_templates = await sync_to_async(RecipeService.get_recipe_templates)()
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
            
            # Stage 3: Generate grocery list (convert sync to async)
            try:
                grocery_list = await sync_to_async(RecipeService.generate_grocery_list)(detailed_recipes)
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