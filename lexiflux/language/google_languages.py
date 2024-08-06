"""Fill the database with languages from Google Translate."""

import json
from typing import Any, Optional

from django.apps import apps as django_apps

SPECIAL_LANGUAGE_CODE_MAPPING = {
    "zh-CN": "zh",  # Chinese (Simplified)
    "zh-TW": "zh",  # Chinese (Traditional)
}


def populate_languages(apps: Optional[django_apps] = None, *args: Any) -> None:  # pylint: disable=keyword-arg-before-vararg
    """Load languages from the JSON file.

    Can be used in RunPython migrations or without params.
    """
    if apps is None:
        language_class = django_apps.get_model("lexiflux", "Language")
    else:
        language_class = apps.get_model("lexiflux", "Language")

    if language_class.objects.exists():
        return  # Languages already populated, no need to do it again

    with open("lexiflux/resources/google_translate_languages.json", "r", encoding="utf8") as file:
        data = json.load(file)

    # Iterate over the languages in the JSON file
    for language in data["languages"]:
        google_code = language["id"]
        epub_code = SPECIAL_LANGUAGE_CODE_MAPPING.get(google_code, google_code)
        lang_name = language["name"]

        # Update or create the language in the database
        language_class.objects.update_or_create(
            google_code=google_code, defaults={"epub_code": epub_code, "name": lang_name}
        )
