from django.urls import path

from . import views

urlpatterns = [
    path("hello/", views.hello, name="hello"),
    path("landing/", views.landing, name="landing"),
    path("recipe-page/", views.recipe_page, name="recipe_page"),
    path("guest-login/", views.guest_login, name="guest_login"),
    path("grocery-list/", views.get_grocery_list, name="get_grocery_list"),
    path("grocery-item/<int:item_id>/", views.get_grocery_item_details, name="get_grocery_item_details"),
    path("grocery-item/<int:item_id>/remove/", views.remove_grocery_item, name="remove_grocery_item"),
    path("get-simulated-recipe-data/", views.get_simulated_recipe_data, name="get_simulated_recipe_data"),
]
