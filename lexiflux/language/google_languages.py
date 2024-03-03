"""Fill the database with languages from Google Translate."""

import json

from ..models import Language  # type: ignore  # pylint: disable=relative-beyond-top-level

SPECIAL_LANGUAGE_CODE_MAPPING = {
    "zh-CN": "zh",  # Chinese (Simplified)
    "zh-TW": "zh",  # Chinese (Traditional)
}


def update_languages() -> None:
    """Load languages from the JSON file."""
    with open("lexiflux/resources/google_translate_languages.json", "r", encoding="utf8") as file:
        data = json.load(file)

    # Iterate over the languages in the JSON file
    for language in data["languages"]:
        google_code = language["id"]
        epub_code = SPECIAL_LANGUAGE_CODE_MAPPING.get(google_code, google_code)
        lang_name = language["name"]

        # Update or create the language in the database
        Language.objects.update_or_create(
            google_code=google_code, defaults={"epub_code": epub_code, "name": lang_name}
        )


# Call the function to update languages
update_languages()
