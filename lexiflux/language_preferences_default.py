"""Create default language preferences"""

from typing import Any

from django.apps import apps

DEFAULT_LEXICAL_ARTICLES = [
    {"type": "Explain", "title": "Explain", "parameters": {"model": "gemini-2.5-flash"}},
    {"type": "Origin", "title": "Origin", "parameters": {"model": "gemini-2.5-flash"}},
    {
        "type": "Lexical",
        "title": "Lexical",
        "parameters": {"model": "gemini-2.5-flash"},
    },
    {
        "type": "Sentence",
        "title": "Sentence",
        "parameters": {"model": "gemini-2.5-flash"},
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
        inline_translation_type="Dictionary",
        inline_translation_parameters={"dictionary": "GoogleTranslator"},
    )

    for article in DEFAULT_LEXICAL_ARTICLES:
        LexicalArticle.objects.create(
            language_preferences=language_preferences,
            type=article["type"],
            title=article["title"],
            parameters=article["parameters"],
        )

    return language_preferences
