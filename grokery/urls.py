"""
URL configuration for groc project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
"""

from django.contrib import admin
from django.urls import path, include
from app import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("start/", views.start, name="start"),
    path("", include("app.urls")),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
]
