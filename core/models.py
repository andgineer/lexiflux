from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):  # type: ignore
    email = models.EmailField(unique=True, blank=False)
    is_approved = models.BooleanField(default=False)
