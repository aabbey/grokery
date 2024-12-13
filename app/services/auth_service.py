from django.contrib.auth import authenticate, login
from django.utils.crypto import get_random_string
from django.contrib.auth import get_user_model

User = get_user_model()

class AuthService:
    @staticmethod
    def create_guest_user():
        guest_email = f"guest_{get_random_string(10)}@guest.local"
        guest_password = get_random_string(12)
        
        guest_user = User.objects.create_user(
            username=guest_email,
            email=guest_email,
            password=guest_password,
            is_guest=True
        )
        
        return guest_user, guest_email, guest_password
    
    @staticmethod
    def authenticate_and_login(request, email, password):
        authenticated_user = authenticate(
            request,
            username=email,
            password=password
        )
        
        if authenticated_user is not None:
            login(request, authenticated_user)
            return True
        return False 