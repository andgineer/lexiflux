"""Create default language preferences"""

from typing import Any

from django.apps import apps

DEFAULT_INLINE_TRANSLATION = {
    "type": "Dictionary",
    "parameters": {"dictionary": "GoogleTranslator"},
}

DEFAULT_LEXICAL_ARTICLES = [
    {
        "type": "AI dictionary",
        "title": "Article",
        "parameters": {"model": "pool"},
    },
    {
        "type": "In depth",
        "title": "In depth",
        "parameters": {"model": "gpt", "effort": "none", "tier": "priority"},
    },
    {
        "type": "Sentence",
        "title": "Sentence",
        "parameters": {"model": "gpt", "effort": "none", "tier": "priority"},
    },
    {
        "type": "Site",
        "title": "glosbe",
        "parameters": {
            "url": "https://glosbe.com/{langCode}/{toLangCode}/{term}",
            "window": True,
        },
    },
]


def create_default_language_preferences(user: Any) -> Any:  # do not use models here
    """Create default language preferences for a user."""
    # Due to circular imports, we need to import the models from the apps
    LanguagePreferences = apps.get_model("lexiflux", "LanguagePreferences")  # noqa: N806
    LexicalArticle = apps.get_model("lexiflux", "LexicalArticle")  # noqa: N806
    Language = apps.get_model("lexiflux", "Language")  # noqa: N806

    try:
        english_language = Language.objects.get(google_code="en")
        serbian_language = Language.objects.get(google_code="sr")
    except Language.DoesNotExist as exc:
        raise ValueError(
            "English and / or Serbian language not found in the Language table.",
        ) from exc

    user_language = user.language if user.language else english_language

    language_preferences = LanguagePreferences.objects.create(
        user=user,
        language=serbian_language,
        user_language=user_language,
        inline_translation_type=DEFAULT_INLINE_TRANSLATION["type"],
        inline_translation_parameters=dict(DEFAULT_INLINE_TRANSLATION["parameters"]),
    )

    for order, article in enumerate(DEFAULT_LEXICAL_ARTICLES):
        LexicalArticle.objects.create(
            language_preferences=language_preferences,
            type=article["type"],
            title=article["title"],
            parameters=dict(article["parameters"]),
            order=order,
        )

    return language_preferences
