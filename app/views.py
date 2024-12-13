from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.utils.crypto import get_random_string
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from django.http import JsonResponse, Http404
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods
import json
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

@login_required(login_url='account_login')
def get_grocery_list(request):
    print("get_grocery_list view called")  # Debug print
    context = {
        'debug': 'This is a test response'
    }
    html = render_to_string('grocery_list_expanded.html', context)
    response_data = {'html': html}
    print("Sending response:", response_data)  # Debug print
    return JsonResponse(response_data)

@login_required(login_url='account_login')
@require_http_methods(["DELETE"])
def remove_grocery_item(request, item_id):
    try:
        # TODO: Replace with actual database query once models are set up
        # item = GroceryItem.objects.get(id=item_id, user=request.user)
        # item.delete()
        
        return JsonResponse({
            'status': 'success',
            'message': f'Item {item_id} removed successfully'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@login_required(login_url='account_login')
def get_grocery_item_details(request, item_id):
    try:
        # TODO: Replace with actual database query
        # item = GroceryItem.objects.get(id=item_id, user=request.user)
        
        # Temporary mock data
        item_details = {
            'id': item_id,
            'name': 'Sample Item',
            'quantity': '2',
            'unit': 'pieces',
            'category': 'Produce',
            'notes': 'Fresh and organic preferred'
        }
        
        html = render_to_string('grocery_item_details.html', {
            'item': item_details
        })
        
        return JsonResponse({
            'status': 'success',
            'html': html
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)
