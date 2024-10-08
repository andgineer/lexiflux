"""Create default language preferences"""

from typing import Any
from django.apps import apps


DEFAULT_LEXICAL_ARTICLES = [
    {"type": "Explain", "title": "Explain 🔗 4o-mini°", "parameters": {"model": "gpt-4o-mini"}},
    {
        "type": "Explain",
        "title": "Explain 💡3.5",
        "parameters": {"model": "claude-3-5-sonnet-20240620"},
    },
    {"type": "Explain", "title": "Explain 🦙3.2", "parameters": {"model": "llama3.2"}},
    {
        "type": "Lexical",
        "title": "Lexical 💡3.5",
        "parameters": {"model": "claude-3-5-sonnet-20240620"},
    },
    {
        "type": "Sentence",
        "title": "Sentence 🔗 4o-mini°",
        "parameters": {"model": "gpt-4o-mini"},
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
    LanguagePreferences = apps.get_model("lexiflux", "LanguagePreferences")  # pylint: disable=invalid-name
    LexicalArticle = apps.get_model("lexiflux", "LexicalArticle")  # pylint: disable=invalid-name
    Language = apps.get_model("lexiflux", "Language")  # pylint: disable=invalid-name

    try:
        english_language = Language.objects.get(google_code="en")
        serbian_language = Language.objects.get(google_code="sr")
    except Language.DoesNotExist as exc:
        raise ValueError(
            "English and / or Serbian language not found in the Language table."
        ) from exc

    language_preferences = LanguagePreferences.objects.create(
        user=user,
        language=serbian_language,
        user_language=english_language,
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
