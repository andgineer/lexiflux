"""Signals for the LexiFlux app."""

from typing import Any
from django.db.models.signals import post_save
from django.dispatch import receiver
from lexiflux.language.google_languages import populate_languages
from lexiflux.language_preferences_default import create_default_language_preferences
from lexiflux.models import CustomUser


@receiver(post_save, sender=CustomUser)  # type: ignore
def create_language_preferences(
    sender: Any,  # pylint: disable=unused-argument
    instance: Any,
    created: Any,
    **kwargs: Any,
) -> None:
    """Create language preferences for a user."""
    if created:
        populate_languages()
        language_preferences = create_default_language_preferences(instance)
        instance.default_language_preferences = language_preferences
        instance.save()
        print(f"Created language preferences for {instance.username}")
