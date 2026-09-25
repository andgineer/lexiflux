"""Create default language preferences"""

from typing import Any

from django.apps import apps

DEFAULT_INLINE_TRANSLATION = {
    "type": "Dictionary",
    "parameters": {"dictionary": "LLMTranslation"},
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

LINGEA_LANGUAGES = {
    "ar": "arapsko",
    "bg": "bugarsko",
    "ca": "katalonsko",
    "cs": "cesko",
    "da": "dansko",
    "de": "nemacko",
    "el": "grcko",
    "en": "englesko",
    "es": "spansko",
    "et": "estonsko",
    "fi": "finsko",
    "fr": "francusko",
    "he": "hebrejsko",
    "hi": "hindsko",
    "hr": "hrvatsko",
    "hu": "madjarsko",
    "id": "indonezansko",
    "it": "italijansko",
    "ja": "japansko",
    "ko": "korejsko",
    "lt": "litvansko",
    "lv": "letonsko",
    "nl": "holandsko",
    "no": "norvesko",
    "pl": "poljsko",
    "pt": "portugalsko",
    "ro": "rumunsko",
    "ru": "rusko",
    "sk": "slovacko",
    "sl": "slovenacko",
    "sv": "svedsko",
    "th": "tajlandsko",
    "tr": "tursko",
    "uk": "ukrajinsko",
    "vi": "vijetnamsko",
    "zh": "kinesko",
    "zh-CN": "kinesko",
    "zh-TW": "kinesko",
}
LINGEA_ARTICLE = {
    "type": "Site",
    "title": "lingea",
    "parameters": {
        "url": "https://recnici.lingea.rs/{toLangLingea}-srpski/{termLatin}",
        "window": True,
    },
}


def is_language_pair_article(parameters: dict[str, Any]) -> bool:
    return parameters.get("url") == LINGEA_ARTICLE["parameters"]["url"]


def add_language_pair_articles(language_preferences: Any) -> None:
    user_language = language_preferences.user_language
    if (
        language_preferences.language.google_code != "sr"
        or not user_language
        or user_language.google_code not in LINGEA_LANGUAGES
    ):
        return
    existing = list(language_preferences.lexical_articles.all())
    if any(
        article.title == LINGEA_ARTICLE["title"] or is_language_pair_article(article.parameters)
        for article in existing
    ):
        return
    language_preferences.lexical_articles.create(
        type=LINGEA_ARTICLE["type"],
        title=LINGEA_ARTICLE["title"],
        parameters=dict(LINGEA_ARTICLE["parameters"]),
        order=max((article.order for article in existing), default=-1) + 1,
    )


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
    # English stands in until the user picks a language; the user modal adds Lingea then.
    if user.language:
        add_language_pair_articles(language_preferences)

    return language_preferences
