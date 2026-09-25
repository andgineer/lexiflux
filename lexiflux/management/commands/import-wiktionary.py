"""Django management command to import the offline Wiktionary."""  # noqa: N999

import argparse
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand

from lexiflux.language.wiktionary import RUSSIAN_EDITION, data_path, wiktionary_code
from lexiflux.language.wiktionary_import import DOWNLOADS_DIR_NAME, import_wiktionary
from lexiflux.models import LanguagePreferences


def default_translation_languages() -> frozenset[str]:
    codes = LanguagePreferences.objects.values_list("user_language__google_code", flat=True)
    return frozenset({RUSSIAN_EDITION, *(wiktionary_code(code) for code in codes if code)})


class Command(BaseCommand):  # type: ignore
    """Download the kaikki.org Wiktionary extracts and build the offline dictionary."""

    help = (
        "Downloads the kaikki.org Wiktionary extracts (English and Russian editions, about "
        "3 GB) and builds the offline dictionary file used by the Wiktionary translator"
    )

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--download-dir",
            type=Path,
            default=None,
            help=f"Where to keep the downloads (default: {DOWNLOADS_DIR_NAME}/ next to the "
            "dictionary file). An interrupted download resumes from there.",
        )
        parser.add_argument(
            "--keep-downloads",
            action="store_true",
            help="Keep the downloads after the import; the next import reuses them "
            "if kaikki.org has not published newer ones",
        )
        parser.add_argument(
            "--translations",
            type=str,
            default=None,
            help="Comma-separated language codes to keep the English words' translations "
            "for (default: Russian plus the user languages set in Language Preferences)",
        )

    def handle(self, *args: Any, **options: Any) -> None:  # noqa: ARG002
        target = data_path()
        download_dir = options["download_dir"] or target.parent / DOWNLOADS_DIR_NAME
        if options["translations"]:
            languages = frozenset(
                wiktionary_code(code.strip())
                for code in options["translations"].split(",")
                if code.strip()
            )
        else:
            languages = default_translation_languages()
        self.stdout.write(
            f"Building {target} (translations: {', '.join(sorted(languages))}); "
            f"downloads in {download_dir}",
        )
        report = import_wiktionary(
            target,
            download_dir,
            languages,
            keep_downloads=options["keep_downloads"],
            progress=self.stdout.write,
        )
        entries = ", ".join(f"{name} {count:,}" for name, count in sorted(report.entries.items()))
        self.stdout.write(
            self.style.SUCCESS(
                f"Wiktionary imported: {report.file_bytes / 1e6:,.0f} MB, entries: {entries}, "
                f"inflected forms: {report.forms:,}. Downloaded "
                f"{report.downloaded_bytes / 1e6:,.0f} MB in {report.download_seconds:.0f} s, "
                f"built in {report.build_seconds:.0f} s.",
            ),
        )
