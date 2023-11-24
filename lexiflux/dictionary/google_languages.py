"""Fill the database with languages from Google Translate."""
import json

from ..models import Language  # type: ignore  # pylint: disable=relative-beyond-top-level


def update_languages() -> None:
    """Load languages from the JSON file."""
    with open("lexiflux/resources/google_translate_languages.json", "r", encoding="utf8") as file:
        data = json.load(file)

    # Iterate over the languages in the JSON file
    for language in data["languages"]:
        lang_code = language["id"]
        lang_name = language["name"]

        # Update or create the language in the database
        Language.objects.update_or_create(code=lang_code, defaults={"name": lang_name})


# Call the function to update languages
update_languages()
