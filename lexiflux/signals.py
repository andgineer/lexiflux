"""Signals for the lexiflux app."""

import json
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from lexiflux.models import ReaderProfile, LexicalArticle, Language

User = get_user_model()

DEFAULT_LEXICAL_ARTICLES = [
    {"type": "Sentence", "title": "Sentence", "parameters": {"model": "gpt-3.5-turbo"}},
    {"type": "Explain", "title": "Explain", "parameters": {"model": "gpt-3.5-turbo"}},
    {"type": "Examples", "title": "Examples", "parameters": {"model": "gpt-3.5-turbo"}},
    {
        "type": "Site",
        "title": "glosbe",
        "parameters": {
            "url": "https://glosbe.com/sr/ru/ff{term}",
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

        reader_profile = ReaderProfile.objects.create(
            user=instance,
            language=serbian_language,
            user_language=english_language,
            inline_translation_type="Dictionary",
            inline_translation_parameters=json.dumps({"dictionary": "GoogleTranslator"}),
        )

        for article in DEFAULT_LEXICAL_ARTICLES:
            LexicalArticle.objects.create(
                reader_profile=reader_profile,
                type=article["type"],
                title=article["title"],
                parameters=article["parameters"],
            )

        # todo: inline_translation


@receiver(post_save, sender=User)  # type: ignore
def save_user_profile(
    sender: Any,  # pylint: disable=unused-argument
    instance: Any,
    **kwargs: Any,
) -> None:
    """Save a profile for a new user."""
    instance.reader_profile.save()
