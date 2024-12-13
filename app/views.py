from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from app.services.auth_service import AuthService

def hello(request):
    return render(request, "hello.html")

def landing(request):
    if request.user.is_authenticated:
        return redirect('start')
    return render(request, "landing.html")

@login_required(login_url='account_login')
def start(request):
    return render(request, "start.html")

@login_required(login_url='account_login')
def recipe_page(request):
    return render(request, "recipe_page.html")

def guest_login(request):
    guest_user, email, password = AuthService.create_guest_user()
    
    if AuthService.authenticate_and_login(request, email, password):
        return redirect('start')
    
    # If authentication fails, delete the created user and show an error
    guest_user.delete()
    return redirect('landing')
