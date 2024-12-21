import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'groc.settings')
django.setup()

from app.services.recipe_service import RecipeService
from app.services.grocery_service import GroceryService
from app.services.auth_service import AuthService

print("\nTesting Recipe Service:")
recipes = RecipeService.get_recipes_and_grocery_list()
print(recipes)

print("\nTesting Grocery Service:")
item = GroceryService.get_item_details(1)
print(item)

print("\nTesting Auth Service:")
user, email, password = AuthService.create_guest_user()
print(f"Created user: {email} with password: {password}") 