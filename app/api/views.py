from django.http import JsonResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
import asyncio

from app.services.recipe_service import RecipeService
from app.services.grocery_service import GroceryService

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
    # Stage 1: Get recipe templates
    recipe_templates = RecipeService.get_recipe_templates()
    print("Recipe templates done")
    
    # Return initial templates immediately
    response = {
        'status': 'loading',
        'recipes': recipe_templates,
        'grocery_list': []
    }
    
    # Stage 2: Get detailed recipes asynchronously
    detailed_recipes = await RecipeService.get_all_recipe_details(recipe_templates)
    print("Detailed recipes done")
    
    # Stage 3: Generate grocery list
    grocery_list = RecipeService.generate_grocery_list(detailed_recipes)
    print("Grocery list done")
    
    # Return final response with all data
    return JsonResponse({
        'status': 'complete',
        'recipes': detailed_recipes,
        'grocery_list': grocery_list
    }) 