"""Signals for the lexiflux app."""

import json
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from lexiflux.models import LanguagePreferences, LexicalArticle, Language

User = get_user_model()

DEFAULT_LEXICAL_ARTICLES = [
    {"type": "Sentence", "title": "Sentence", "parameters": {"model": "gpt-3.5-turbo"}},
    {"type": "Explain", "title": "Explain", "parameters": {"model": "gpt-4-turbo"}},
    {"type": "Examples", "title": "Examples", "parameters": {"model": "gpt-3.5-turbo"}},
    {
        "type": "Site",
        "title": "glosbe",
        "parameters": {
            "url": "https://glosbe.com/sr/ru/{term}",
            "window": True,
        },
    },
]


@receiver(post_save, sender=User)  # type: ignore
def create_user_profile(
    sender: Any,  # pylint: disable=unused-argument
    instance: Any,
    created: Any,
    **kwargs: Any,
) -> None:
    """Create a profile and default lexical articles for a new user."""
    if created:
        try:
            english_language = Language.objects.get(google_code="en")
            serbian_language = Language.objects.get(google_code="sr")
        except Language.DoesNotExist as exc:
            raise ValueError(
                "English and / or Serbian language not found in the Language table."
            ) from exc

        language_preferences = LanguagePreferences.objects.create(
            user=instance,
            language=serbian_language,
            user_language=english_language,
            inline_translation_type="Dictionary",
            inline_translation_parameters=json.dumps({"dictionary": "GoogleTranslator"}),
        )
        instance.default_language_preferences = language_preferences
        instance.save()

        for article in DEFAULT_LEXICAL_ARTICLES:
            LexicalArticle.objects.create(
                reader_profile=language_preferences,
                type=article["type"],
                title=article["title"],
                parameters=article["parameters"],
            )
