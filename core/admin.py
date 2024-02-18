"""Custom User Admin Configuration"""
from django.contrib import admin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):  # type: ignore
    """Custom User Admin Configuration."""

    list_display = ["username", "email", "is_approved"]
    list_editable = ["is_approved"]
