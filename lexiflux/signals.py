"""Signals for the lexiflux app."""
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ReaderProfile

User = get_user_model()


@receiver(post_save, sender=User)  # type: ignore
def create_user_profile(
    sender: Any, instance: Any, created: Any, **kwargs: Any  # pylint: disable=unused-argument
) -> None:  # pylint: disable=unused-argument
    """Create a profile for a new user."""
    if created:
        ReaderProfile.objects.create(user=instance)


@receiver(post_save, sender=User)  # type: ignore
def save_user_profile(
    sender: Any, instance: Any, **kwargs: Any  # pylint: disable=unused-argument
) -> None:
    """Save a profile for a new user."""
    instance.readerprofile.save()
