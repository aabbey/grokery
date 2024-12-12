from django.urls import path

from . import views

urlpatterns = [
    path("hello/", views.hello, name="hello"),
    path("landing/", views.landing, name="landing"),
    path("recipe-page/", views.recipe_page, name="recipe_page"),
    path("guest-login/", views.guest_login, name="guest_login"),
]
