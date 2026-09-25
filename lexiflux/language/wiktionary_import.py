"""Build the offline Wiktionary file from the kaikki.org raw Wiktionary extracts."""

import contextlib
import gzip
import json
import os
import re
import sqlite3
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from lexiflux.language.wiktionary import ENGLISH_EDITION, RUSSIAN_EDITION, lookup_key


@dataclass(frozen=True)
class Source:
    edition: str
    url: str
    languages: dict[str, str]

    @property
    def file_name(self) -> str:
        return f"{self.edition}wiktionary.jsonl.gz"


# kaikki.org deprecated its per-language files; the raw edition dumps are filtered by language.
SOURCES = (
    Source(
        RUSSIAN_EDITION,
        "https://kaikki.org/ruwiktionary/raw-wiktextract-data.jsonl.gz",
        {"en": "en", "de": "de", "sr": "sh"},
    ),
    Source(
        ENGLISH_EDITION,
        "https://kaikki.org/dictionary/raw-wiktextract-data.jsonl.gz",
        {"en": "en", "de": "de", "sh": "sh"},
    ),
)
DOWNLOADS_DIR_NAME = "wiktionary-downloads"
USER_AGENT = "lexiflux (https://github.com/andgineer/lexiflux)"
CHUNK_BYTES = 1 << 20
BATCH_ROWS = 10_000
PROGRESS_STEPS = 10
SKIPPED_POS = frozenset({"romanization", "character", "symbol"})
# Spellings nobody prints would drag unrelated lemmas in ("free" as a spelling of "three").
NOISE_TAGS = frozenset({"pronunciation-spelling", "misspelling", "eye-dialect"})
# Such a link would rank an unrelated lemma above the word itself ("SHE" → health, dialectal
# "be" → by).
UNLINKED_SENSE_TAGS = frozenset(
    {"abbreviation", "initialism", "acronym", "obsolete", "archaic", "dialectal", "dated"},
)
# Table labels, template names, auxiliaries and multi-word tenses are not spellings of the word.
# An "alternative" form is the main spelling listed on a variant's page ("bear" on "ber").
SKIPPED_FORM_TAGS = NOISE_TAGS | {
    "alternative",
    "table-tags",
    "inflection-template",
    "error-unrecognized-form",
    "auxiliary",
    "includes-article",
    "multiword-construction",
    "romanization",
}
OPTIONAL_PART = re.compile(r"\(([^()]*)\)")

SCHEMA = """
CREATE TABLE entries (
    lang TEXT NOT NULL,
    edition TEXT NOT NULL,
    key TEXT NOT NULL,
    word TEXT NOT NULL,
    pos TEXT NOT NULL,
    senses TEXT NOT NULL,
    translations TEXT
);
CREATE TEMP TABLE links (lang TEXT NOT NULL, form TEXT NOT NULL, lemma TEXT NOT NULL);
"""
FINISH = """
CREATE INDEX entries_key ON entries (key, lang);
CREATE TABLE forms (
    form TEXT NOT NULL,
    lang TEXT NOT NULL,
    lemma TEXT NOT NULL,
    PRIMARY KEY (form, lang, lemma)
) WITHOUT ROWID;
INSERT INTO forms
    SELECT DISTINCT form, lang, lemma FROM temp.links AS link
    WHERE EXISTS (SELECT 1 FROM entries WHERE entries.key = link.lemma AND entries.lang = link.lang)
    ORDER BY form, lang, lemma;
DROP TABLE temp.links;
"""

Progress = Callable[[str], None]


@dataclass
class ImportReport:
    downloaded_bytes: int = 0
    download_seconds: float = 0.0
    build_seconds: float = 0.0
    entries: dict[str, int] = field(default_factory=dict)
    forms: int = 0
    file_bytes: int = 0


def http_client() -> httpx.Client:
    return httpx.Client(
        follow_redirects=True,
        timeout=httpx.Timeout(60.0, connect=30.0),
        headers={"User-Agent": USER_AGENT},
    )


def _megabytes(size: int) -> str:
    return f"{size / 1e6:,.0f} MB"


def download(client: httpx.Client, url: str, target: Path, progress: Progress) -> int:
    partial = target.with_name(target.name + ".part")
    etag_file = target.with_name(target.name + ".etag")
    etag = etag_file.read_text().strip() if etag_file.is_file() else ""
    headers = {}
    if etag and target.is_file():
        headers["If-None-Match"] = etag
    elif etag and partial.is_file():
        headers["Range"] = f"bytes={partial.stat().st_size}-"
        headers["If-Range"] = etag
    with client.stream("GET", url, headers=headers) as response:
        if response.status_code == httpx.codes.NOT_MODIFIED:
            progress(f"{target.name}: unchanged since the last download")
            return 0
        if response.status_code == httpx.codes.REQUESTED_RANGE_NOT_SATISFIABLE:
            partial.unlink()
            return download(client, url, target, progress)
        response.raise_for_status()
        resumed = response.status_code == httpx.codes.PARTIAL_CONTENT
        new_etag = response.headers.get("etag", "")
        if new_etag and not new_etag.startswith("W/"):
            etag_file.write_text(new_etag)
        else:
            etag_file.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        offset = partial.stat().st_size if resumed else 0
        total = offset + int(response.headers.get("content-length", 0))
        progress(
            f"{target.name}: downloading {_megabytes(total)}"
            + (f", resuming at {_megabytes(offset)}" if resumed else ""),
        )
        transferred = 0
        next_report = offset + total // PROGRESS_STEPS
        with partial.open("ab" if resumed else "wb") as file:
            for chunk in response.iter_raw(CHUNK_BYTES):
                file.write(chunk)
                transferred += len(chunk)
                if total and offset + transferred >= next_report:
                    progress(f"{target.name}: {_megabytes(offset + transferred)}")
                    next_report += total // PROGRESS_STEPS
    partial.replace(target)
    return transferred


def records(path: Path, source: Source, progress: Progress) -> Iterator[tuple[str, dict[str, Any]]]:
    codes = b"|".join(re.escape(code.encode()) for code in source.languages)
    # A cheap test before parsing: most lines are words of other languages.
    candidate = re.compile(rb'"lang_code":\s*"(?:' + codes + rb')"')
    size = path.stat().st_size
    next_report = size // PROGRESS_STEPS
    with path.open("rb") as raw, gzip.GzipFile(fileobj=raw) as lines:
        for line in lines:
            if raw.tell() >= next_report:
                progress(f"{path.name}: {100 * raw.tell() // size}% read")
                next_report += size // PROGRESS_STEPS
            if candidate.search(line) is None:
                continue
            record = json.loads(line)
            language = source.languages.get(record.get("lang_code", ""))
            if language:
                yield language, record


def _spellings(form: str) -> list[str]:
    # "Pfirsich(e)" stands for "Pfirsich" and "Pfirsiche".
    optional = OPTIONAL_PART.search(form)
    if optional is None:
        return [form]
    before, after = form[: optional.start()], form[optional.end() :]
    return [before + after, before + optional.group(1) + after]


def _forms(record: dict[str, Any], language: str) -> set[str]:
    return {
        lookup_key(spelling, language)
        for form in record.get("forms", [])
        if form.get("form") and not SKIPPED_FORM_TAGS.intersection(form.get("tags", []))
        for spelling in _spellings(form["form"])
    }


def _translations(
    record: dict[str, Any],
    languages: frozenset[str],
) -> dict[str, list[tuple[str, list[str]]]]:
    groups: dict[str, dict[str, list[str]]] = {}
    for translation in record.get("translations", []):
        code = translation.get("lang_code") or translation.get("code")
        if code in languages and translation.get("word"):
            by_sense = groups.setdefault(code, {})
            by_sense.setdefault(translation.get("sense") or "", []).append(translation["word"])
    return {
        code: [(sense, list(dict.fromkeys(words))) for sense, words in by_sense.items()]
        for code, by_sense in groups.items()
    }


def prune(
    record: dict[str, Any],
    language: str,
    edition: str,
    translation_languages: frozenset[str],
) -> tuple[tuple[str, ...] | None, set[tuple[str, str]]]:
    word, pos = record.get("word"), record.get("pos")
    if not word or not pos or pos in SKIPPED_POS:
        return None, set()
    key = lookup_key(word, language)
    glosses: list[str] = []
    lemmas: set[str] = set()
    for sense in record.get("senses", []):
        tags = sense.get("tags", [])
        if NOISE_TAGS.intersection(tags):
            continue
        targets = [
            link["word"]
            for link in sense.get("form_of", []) + sense.get("alt_of", [])
            if link.get("word")
        ]
        if targets:
            if not UNLINKED_SENSE_TAGS.intersection(tags):
                lemmas.update(lookup_key(target, language) for target in targets)
        elif sense.get("glosses"):
            # English-edition sub-senses repeat their parents' glosses first.
            glosses.append(sense["glosses"][-1])
    links = {(form, key) for form in _forms(record, language)}
    links |= {(key, lemma) for lemma in lemmas}
    links = {(form, lemma) for form, lemma in links if form and lemma and form != lemma}
    translations = (
        _translations(record, translation_languages) if edition == ENGLISH_EDITION else {}
    )
    if not glosses and not translations:
        return None, links
    row = (
        language,
        edition,
        key,
        word,
        pos,
        json.dumps(list(dict.fromkeys(glosses)), ensure_ascii=False),
        json.dumps(translations, ensure_ascii=False) if translations else None,
    )
    return row, links


def _write_source(  # noqa: PLR0913
    db: sqlite3.Connection,
    path: Path,
    source: Source,
    translation_languages: frozenset[str],
    report: ImportReport,
    progress: Progress,
) -> None:
    rows: list[tuple[str, ...]] = []
    links: list[tuple[str, str, str]] = []

    def flush() -> None:
        db.executemany("INSERT INTO entries VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
        db.executemany("INSERT INTO temp.links VALUES (?, ?, ?)", links)
        rows.clear()
        links.clear()

    for language, record in records(path, source, progress):
        row, entry_links = prune(record, language, source.edition, translation_languages)
        if row:
            rows.append(row)
            name = f"{source.edition}-{language}"
            report.entries[name] = report.entries.get(name, 0) + 1
        links.extend((language, form, lemma) for form, lemma in entry_links)
        if len(rows) + len(links) >= BATCH_ROWS:
            flush()
    flush()


def build(
    target: Path,
    downloads: list[tuple[Source, Path]],
    translation_languages: frozenset[str],
    report: ImportReport,
    progress: Progress,
) -> None:
    building = target.with_name(target.name + ".building")
    building.unlink(missing_ok=True)
    try:
        db = sqlite3.connect(building)
        try:
            db.executescript("PRAGMA journal_mode = OFF; PRAGMA synchronous = OFF;" + SCHEMA)
            for source, path in downloads:
                _write_source(db, path, source, translation_languages, report, progress)
            progress("Indexing inflected forms")
            db.executescript(FINISH)
            db.commit()
            report.forms = db.execute("SELECT count(*) FROM forms").fetchone()[0]
        finally:
            db.close()
        # A reader never sees a half-built file: the rebuild replaces it in one step.
        os.replace(building, target)
    finally:
        building.unlink(missing_ok=True)
    report.file_bytes = target.stat().st_size


def import_wiktionary(  # noqa: PLR0913
    target: Path,
    download_dir: Path,
    translation_languages: frozenset[str],
    keep_downloads: bool = False,
    progress: Progress = print,
    client: httpx.Client | None = None,
) -> ImportReport:
    report = ImportReport()
    download_dir.mkdir(parents=True, exist_ok=True)
    downloads = [(source, download_dir / source.file_name) for source in SOURCES]
    started = time.monotonic()
    with client or http_client() as http:
        for source, path in downloads:
            report.downloaded_bytes += download(http, source.url, path, progress)
    report.download_seconds = time.monotonic() - started
    started = time.monotonic()
    build(target, downloads, translation_languages, report, progress)
    report.build_seconds = time.monotonic() - started
    if not keep_downloads:
        for _source, path in downloads:
            path.unlink(missing_ok=True)
            path.with_name(path.name + ".etag").unlink(missing_ok=True)
        with contextlib.suppress(OSError):
            download_dir.rmdir()
    return report
