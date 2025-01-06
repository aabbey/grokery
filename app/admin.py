from django.contrib import admin
from .models import User, UserCurrentRecipes, UserGroceryList

# Register the User model
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_guest', 'cooking_skill_level', 'household_size', 'created_at')
    search_fields = ('username', 'email')
    list_filter = ('is_guest', 'cooking_skill_level')

# Register the UserCurrentRecipes model
@admin.register(UserCurrentRecipes)
class UserCurrentRecipesAdmin(admin.ModelAdmin):
    list_display = ('user', 'updated_at')
    search_fields = ('user__username',)

# Register the UserGroceryList model
@admin.register(UserGroceryList)
class UserGroceryListAdmin(admin.ModelAdmin):
    list_display = ('user', 'updated_at')
    search_fields = ('user__username',)
