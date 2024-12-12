from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.utils.crypto import get_random_string
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
User = get_user_model()

# Create your views here.
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
    # Create a guest user with a random username
    guest_email = f"guest_{get_random_string(10)}@guest.local"
    guest_password = get_random_string(12)
    
    guest_user = User.objects.create_user(
        username=guest_email,
        email=guest_email,
        password=guest_password,
        is_guest=True
    )
    
    # Authenticate the user first
    authenticated_user = authenticate(
        request,
        username=guest_email,
        password=guest_password
    )
    
    if authenticated_user is not None:
        login(request, authenticated_user)
        return redirect('start')
    
    # If authentication fails, delete the created user and show an error
    guest_user.delete()
    return redirect('landing')