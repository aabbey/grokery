from django.urls import path
from django.views.generic.base import RedirectView
from app.api import views as api_views
from . import views

urlpatterns = [
    # Redirect root to recipe page
    path('', RedirectView.as_view(url='/recipes/', permanent=False), name='index'),
    path('recipes/', views.recipe_page, name='recipe_page'),
    
    # Auth endpoints
    path('guest-login/', views.guest_login, name='guest_login'),
    
    # API endpoints
    path('api/recipes/generate/', api_views.stream_recipe_generation, name='stream_recipe_generation'),
    path('api/grocery-list/', api_views.get_grocery_list, name='get_grocery_list'),
    path('api/grocery-item/<int:item_id>/', api_views.get_grocery_item_details, name='get_grocery_item_details'),
    path('api/grocery-item/<int:item_id>/remove/', api_views.remove_grocery_item, name='remove_grocery_item'),
    path('preferences-modal/', views.preferences_modal, name='preferences_modal'),
]
