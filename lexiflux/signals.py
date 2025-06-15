"""Signals for the LexiFlux app."""

import logging
from typing import Any

from django.db.models import Model
from django.db.models.signals import post_save
from django.dispatch import receiver

from lexiflux.language.google_languages import populate_languages
from lexiflux.language_preferences_default import create_default_language_preferences
from lexiflux.models import CustomUser

logger = logging.getLogger(__name__)  # Use __name__ for proper module-level logging


@receiver(post_save, sender=CustomUser)  # type: ignore
def create_language_preferences(
    sender: type[Model],  # noqa: ARG001
    instance: CustomUser,
    created: bool,
    raw: bool = False,
    **kwargs: Any,  # noqa: ARG001
) -> None:
    """Create language preferences for a new user.

    Args:
        sender: The model class that sent the signal
        instance: The actual instance being saved
        created: Boolean indicating if this is a new instance
        raw: Boolean; True if model is saved exactly as presented

    """
    # Skip if this is a raw save (e.g., from loaddata)
    if raw:
        return

    # Only proceed if this is a new user and they don't have default preferences yet
    if created and not instance.default_language_preferences:
        try:
            # Ensure languages exist
            populate_languages()

            # Create default language preferences
            language_preferences = create_default_language_preferences(instance)

            # Update user with new preferences, but avoid recursive signal
            CustomUser.objects.filter(pk=instance.pk).update(
                default_language_preferences=language_preferences,
            )

            # Update instance to match database
            instance.refresh_from_db()

            logger.info(
                f"Successfully created language preferences for user {instance.username} "
                f"(ID: {instance.pk})",
            )

        except Exception as e:
            logger.error(
                f"Failed to create language preferences for user {instance.username} "
                f"(ID: {instance.pk}): {str(e)}",
            )
            raise
