from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # Additional fields for user preferences
    is_guest = models.BooleanField(default=False)
    dietary_preferences = models.JSONField(default=dict, blank=True)
    cooking_skill_level = models.CharField(
        max_length=20,
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced')
        ],
        default='beginner'
    )
    preferred_cuisine_types = models.JSONField(default=list, blank=True)
    max_recipe_time = models.IntegerField(default=60)  # in minutes
    household_size = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'auth_user'
