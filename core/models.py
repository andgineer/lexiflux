"""Custom user model for the application."""
from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):  # type: ignore
    """Custom user model for the application."""

    email = models.EmailField(unique=True, blank=False)
    is_approved = models.BooleanField(default=False)
