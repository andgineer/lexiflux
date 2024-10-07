"""Word export to CSV file."""

import csv
import io
from typing import List

from django.core.files.base import ContentFile
from django.utils import timezone

from lexiflux.models import Language, TranslationHistory


def export_words_to_csv_file(
    language: Language, terms: List[TranslationHistory]
) -> tuple[ContentFile, str]:
    """Export words to a CSV file."""
    filename = f"lexiflux_{language.google_code}_" f"{timezone.now().strftime('%Y%m%d%H%M%S')}.csv"

    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(["Term", "Translation", "Language", "Translation Language", "Sentence"])

    for term in terms:
        context_parts = term.context.split(TranslationHistory.CONTEXT_MARK)
        sentence_start = context_parts[1]
        sentence_end = context_parts[2]

        full_sentence = f"{sentence_start}_____{sentence_end}"

        writer.writerow(
            [
                term.term,
                term.translation,
                term.source_language.name,
                term.target_language.name,
                full_sentence,
            ]
        )

    output.seek(0)
    content_file = ContentFile(output.getvalue().encode("utf-8"), name=filename)

    return content_file, filename
