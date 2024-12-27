import os
import django
import asyncio

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'groc.settings')
django.setup()

from app.services.recipe_service import RecipeService
from app.services.grocery_service import GroceryService
from app.services.auth_service import AuthService

async def test_recipe_service():
    print("\nTesting Recipe Service:")
    # Get recipe templates
    templates = await RecipeService.get_recipe_templates()
    print("Recipe templates:", templates)
    
    # Get detailed recipes
    detailed_recipes = await RecipeService.get_all_recipe_details(templates)
    print("Detailed recipes:", detailed_recipes)
    
    # Generate grocery list
    grocery_list = await RecipeService.generate_grocery_list(detailed_recipes)
    print("Grocery list:", grocery_list)
    return detailed_recipes, grocery_list

def test_grocery_service():
    print("\nTesting Grocery Service:")
    item = GroceryService.get_item_details(1)
    print(item)

def test_auth_service():
    print("\nTesting Auth Service:")
    user, email, password = AuthService.create_guest_user()
    print(f"Created user: {email} with password: {password}")

async def main():
    # Run recipe service tests
    await test_recipe_service()
    
    # Run synchronous tests
    test_grocery_service()
    test_auth_service()

if __name__ == "__main__":
    asyncio.run(main()) 