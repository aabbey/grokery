from django.urls import path
from . import views
from .api import views as api_views

urlpatterns = [
    # Page routes (excluding those defined in root urls.py)
    path('hello/', views.hello, name='hello'),
    path('recipe/', views.recipe_page, name='recipe_page'),
    path('guest-login/', views.guest_login, name='guest_login'),
    
    # API routes
    path('api/grocery-list/', api_views.get_grocery_list, name='get_grocery_list'),
    path('api/grocery-item/<int:item_id>/', api_views.get_grocery_item_details, name='get_grocery_item_details'),
    path('api/grocery-item/<int:item_id>/remove/', api_views.remove_grocery_item, name='remove_grocery_item'),
    path('api/recipe-data/', api_views.get_simulated_recipe_data, name='get_simulated_recipe_data'),
]
