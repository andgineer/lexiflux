"""Fill the database with languages from Google Translate."""

import json
from typing import Any, Optional

from django.apps import apps as django_apps

SPECIAL_LANGUAGE_CODE_MAPPING = {
    "zh-CN": "zh",  # Chinese (Simplified)
    "zh-TW": "zh",  # Chinese (Traditional)
}

LANGUAGE_GROUPS: dict[str, list[str]] = {
    "Serbo-Croatian": ["Serbian", "Croatian", "Bosnian"],
    "Chinese": ["Chinese (Simplified)", "Chinese (Traditional)"],
    "Arabic": ["Arabic", "Egyptian Arabic"],
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

    with open("lexiflux/resources/google_translate_languages.json", encoding="utf8") as file:
        data = json.load(file)

    # Iterate over the languages in the JSON file
    for language in data["languages"]:
        google_code = language["id"]
        epub_code = SPECIAL_LANGUAGE_CODE_MAPPING.get(google_code, google_code)
        lang_name = language["name"]

        # Update or create the language in the database
        language_class.objects.update_or_create(
            google_code=google_code,
            defaults={"epub_code": epub_code, "name": lang_name},
        )

    populate_language_groups(apps, *args)


def populate_language_groups(apps: Optional[django_apps] = None, *args: Any) -> None:  # pylint: disable=keyword-arg-before-vararg  # noqa: ARG001
    """Load language groups."""
    get_model = django_apps.get_model if apps is None else apps.get_model
    try:
        language_class = get_model("lexiflux", "Language")
        language_group_class = get_model("lexiflux", "LanguageGroup")
    except LookupError as e:
        print(f"Error: {e}")
        print("Skipping language group population.")
        return

    for group_name, languages in LANGUAGE_GROUPS.items():
        group, created = language_group_class.objects.get_or_create(name=group_name)

        if created:
            for lang_name in languages:
                try:
                    language = language_class.objects.get(name=lang_name)
                    group.languages.add(language)
                except language_class.DoesNotExist:
                    print(
                        f"Warning: {lang_name} not found in the database for group {group_name}.",
                    )

            group.save()
            print(f"{group_name} language group created successfully.")
        else:
            print(f"{group_name} language group already exists.")
