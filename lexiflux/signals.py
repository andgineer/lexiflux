"""Signals for the lexiflux app."""

from typing import Any

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ReaderProfile, LexicalArticle

User = get_user_model()

DEFAULT_LEXICAL_ARTICLES = [
    {"type": "Sentence", "title": "Sentence", "parameters": {"model": "gpt-3.5-turbo"}},
    {"type": "Explain", "title": "Explain", "parameters": {"model": "gpt-3.5-turbo"}},
    {
        "type": "Dictionary",
        "title": "merriam-webster",
        "parameters": {"dictionary": "merriam-webster"},
    },
    {
        "type": "Site",
        "title": "translate.google",
        "parameters": {
            "url": "https://translate.google.com/?sl=en&tl=sr&text={term}&op=translate",
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
        reader_profile = ReaderProfile.objects.create(user=instance)

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
