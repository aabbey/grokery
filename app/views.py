from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from app.services.auth_service import AuthService
from django.template.loader import render_to_string
from django.http import HttpResponse
from app.models import UserCurrentRecipes, UserGroceryList
import logging
import json

logger = logging.getLogger(__name__)

def landing(request):
    if request.user.is_authenticated:
        return redirect('recipe_page')
    return render(request, "landing.html")

@login_required(login_url='account_login')
def recipe_page(request):
    logger.info(f"Loading recipe page for user: {request.user.id} ({request.user.username})")
    
    # Get user's current recipes
    recipes = UserCurrentRecipes.objects.filter(user=request.user).first()
    logger.info(f"Found UserCurrentRecipes record: {recipes is not None}")
    if recipes:
        logger.info(f"Recipe count: {len(recipes.recipes) if recipes.recipes else 0}")
        logger.info(f"Recipe data: {json.dumps(recipes.recipes, indent=2)}")
        
        # Log recipe details for debugging
        if recipes.recipes:
            for recipe in recipes.recipes:
                logger.info(f"Recipe {recipe.get('id')}: {recipe.get('title')}")
                logger.info(f"  - Ingredients: {len(recipe.get('ingredients', []))} items")
                logger.info(f"  - Instructions: {len(recipe.get('instructions', []))} steps")
                logger.info(f"  - Has image: {bool(recipe.get('image'))}")
    else:
        logger.warning("No recipes found for user")
    
    # Get user's grocery list
    grocery_list = UserGroceryList.objects.filter(user=request.user).first()
    logger.info(f"Found UserGroceryList record: {grocery_list is not None}")
    if grocery_list:
        logger.info(f"Grocery item count: {len(grocery_list.items) if grocery_list.items else 0}")
        logger.info(f"Grocery list data: {json.dumps(grocery_list.items, indent=2)}")
        
        # Log grocery list details for debugging
        if grocery_list.items:
            for item in grocery_list.items:
                logger.info(f"Grocery item: {item.get('name')} - {item.get('quantity')} {item.get('unit')}")
    else:
        logger.warning("No grocery list found for user")
    
    # Prepare context
    context = {
        'has_recipes': bool(recipes and recipes.recipes),
        'has_grocery_list': bool(grocery_list and grocery_list.items),
        'recipes': recipes.recipes if recipes else [],
        'grocery_list': grocery_list.items if grocery_list else [],
    }
    
    logger.info(f"Context prepared: has_recipes={context['has_recipes']}, has_grocery_list={context['has_grocery_list']}")
    logger.info(f"Sending recipes count: {len(context['recipes'])}")
    logger.info(f"Sending grocery items count: {len(context['grocery_list'])}")
    
    return render(request, "recipe_page.html", context)

def guest_login(request):
    guest_user, email, password = AuthService.create_guest_user()
    
    if AuthService.authenticate_and_login(request, email, password):
        return redirect('recipe_page')
    
    # If authentication fails, delete the created user and show an error
    guest_user.delete()
    return redirect('landing')

def preferences_modal(request):
    html = render_to_string('preferences_modal.html')
    return HttpResponse(html)
