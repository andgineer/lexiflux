"""Offline Wiktionary: senses for a word from the pruned kaikki.org data."""

import json
import re
import sqlite3
import unicodedata
import urllib.parse
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.utils.html import escape, format_html, format_html_join
from django.utils.safestring import SafeString, mark_safe

ENGLISH_EDITION = "en"
RUSSIAN_EDITION = "ru"
SERBO_CROATIAN = "sh"
GERMAN = "de"
# Wiktionary files Serbian, Croatian and Bosnian, and their translations, as Serbo-Croatian.
DATA_LANGUAGES = {"en": "en", "de": "de", "sr": "sh", "hr": "sh", "bs": "sh"}
DATA_LANGUAGE_NAMES = {"en": "English", "de": "German", "sh": "Serbo-Croatian"}

LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"
MAX_SENSES = 12
POS_LABELS = {
    "adj": "adjective",
    "adv": "adverb",
    "article": "article",
    "conj": "conjunction",
    "det": "determiner",
    "interj": "interjection",
    "intj": "interjection",
    "name": "proper noun",
    "noun": "noun",
    "num": "numeral",
    "particle": "particle",
    "phrase": "phrase",
    "prep": "preposition",
    "prep_phrase": "prepositional phrase",
    "pron": "pronoun",
    "verb": "verb",
    "unknown": "",
}

CARON = "̌"
ACUTE = "́"
GRAVE = "̀"
STRESS_MARKS = str.maketrans("", "", ACUTE + GRAVE)
EDGE_PUNCTUATION = ' \t\r\n.,;:!?"()[]{}«»„“”‚…—–'
SERBIAN_CYRILLIC = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "ђ": "đ",
    "е": "e",
    "ж": "ž",
    "з": "z",
    "и": "i",
    "ј": "j",
    "к": "k",
    "л": "l",
    "љ": "lj",
    "м": "m",
    "н": "n",
    "њ": "nj",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "ћ": "ć",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "c",
    "ч": "č",
    "џ": "dž",
    "ш": "š",
}
CYRILLIC_TO_LATIN = str.maketrans(
    {
        **SERBIAN_CYRILLIC,
        **{char.upper(): latin.capitalize() for char, latin in SERBIAN_CYRILLIC.items()},
    },
)


# Leading usage labels of Russian-edition senses ("экон.", "с.-х.", "мн. ч.", "устар. или поэт.");
# labels right before "от" are kept whole: "сокр. от ..." reads as "abbreviation of ...".
RUSSIAN_LABEL = r"[а-яё]+(?:\.-[а-яё]+)*\.(?:\s[а-яё]\.(?!-))*"
RUSSIAN_USAGE_LABELS = re.compile(
    rf"^(?:{RUSSIAN_LABEL}(?:\s+(?:и|или)\s+{RUSSIAN_LABEL})*(?:,\s*|\s+)(?![а-яё]\.(?!-)))+(?!от\s)",
)


class WiktionaryNotInstalledError(Exception):
    pass


@dataclass(frozen=True)
class Sense:
    text: str
    note: str = ""


@dataclass(frozen=True)
class Entry:
    word: str
    pos: str
    edition: str
    language: str
    senses: tuple[Sense, ...]
    in_user_language: bool


def data_path() -> Path:
    return Path(settings.WIKTIONARY_DATABASE)


def data_language(language_code: str) -> str | None:
    return DATA_LANGUAGES.get(language_code)


def wiktionary_code(language_code: str) -> str:
    code = language_code.split("-")[0].lower()
    return DATA_LANGUAGES.get(code, code)


def _strip_accents(text: str) -> str:
    # Wiktionary marks Serbo-Croatian pitch accents that books never print; č, š, ž, ć stay.
    kept: list[str] = []
    for char in unicodedata.normalize("NFD", text):
        if unicodedata.combining(char) and not (
            char == CARON or (char == ACUTE and kept and kept[-1] == "c")
        ):
            continue
        kept.append(char)
    return unicodedata.normalize("NFC", "".join(kept))


def serbian_latin(text: str) -> str:
    return text.translate(CYRILLIC_TO_LATIN)


def lookup_key(text: str, language: str) -> str:
    key = " ".join(text.replace("’", "'").split()).lower()
    if language == SERBO_CROATIAN:
        key = serbian_latin(_strip_accents(key))
    return key


def _entry(
    row: tuple[str, str, str, str, str, str | None],
    language: str,
    user_language: str,
) -> Entry:
    _key, edition, word, pos, glosses, translations = row
    equivalents = json.loads(translations).get(user_language) if translations else None
    if equivalents:
        senses = tuple(Sense(", ".join(words), note) for note, words in equivalents)
    else:
        senses = tuple(Sense(gloss) for gloss in json.loads(glosses))
    return Entry(
        word=word,
        pos=pos,
        edition=edition,
        language=language,
        senses=senses,
        in_user_language=bool(equivalents) or edition == user_language,
    )


def _is_cyrillic(text: str) -> bool:
    return any("\u0400" <= char <= "\u04ff" for char in text)


def _one_script(group: list[tuple[int, Entry]], cyrillic: bool) -> list[tuple[int, Entry]]:
    # The same Serbo-Croatian lemma often has an entry per script; the fuller one wins.
    scripts: dict[bool, list[tuple[int, Entry]]] = {}
    for item in group:
        scripts.setdefault(_is_cyrillic(item[1].word), []).append(item)
    return max(
        scripts.items(),
        key=lambda script: (
            sum(len(entry.senses) for _, entry in script[1]),
            script[0] == cyrillic,
        ),
    )[1]


def _rows(path: Path, key: str, language: str) -> tuple[list[str], list[tuple]]:
    with closing(sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)) as db:
        lemmas = list(
            dict.fromkeys(
                [key]
                + [
                    lemma
                    for (lemma,) in db.execute(
                        "SELECT lemma FROM forms WHERE form = ? AND lang = ?",
                        (key, language),
                    )
                ],
            ),
        )
        placeholders = ",".join("?" * len(lemmas))
        rows = db.execute(
            "SELECT key, edition, word, pos, senses, translations FROM entries "  # noqa: S608
            f"WHERE lang = ? AND key IN ({placeholders}) ORDER BY rowid",
            (language, *lemmas),
        ).fetchall()
    return lemmas, rows


def lookup(
    text: str,
    language_code: str,
    user_language_code: str,
    path: Path | None = None,
) -> list[Entry]:
    language = data_language(language_code)
    if language is None:
        return []
    path = path or data_path()
    if not path.is_file():
        raise WiktionaryNotInstalledError(str(path))
    user_language = wiktionary_code(user_language_code)
    typed = text.strip(EDGE_PUNCTUATION)
    lemmas, rows = _rows(path, lookup_key(typed, language), language)
    # Russian glosses help only a Russian reader; the English edition is the fallback for all.
    editions = [ENGLISH_EDITION]
    if user_language == RUSSIAN_EDITION:
        editions.insert(0, RUSSIAN_EDITION)
    # A capital marks a German noun ("Schloss" before "schloss" of "schließen"); elsewhere it
    # is mostly a sentence start, and a capitalised twin is a name ("Spring", a surname).
    wanted = typed if language == GERMAN else typed.lower()
    groups: dict[int, dict[int, list[tuple[int, Entry]]]] = {}
    for index, row in enumerate(rows):
        lemma = lemmas.index(row[0])
        # A name reached through a spelling is someone's surname, not the word.
        if row[1] not in editions or (lemma and row[3] == "name"):
            continue
        if (entry := _entry(row, language, user_language)).senses:
            by_edition = groups.setdefault(lemma, {})
            by_edition.setdefault(editions.index(row[1]), []).append((index, entry))
    ranked: list[tuple[bool, int, int, list[Entry]]] = []
    for lemma, by_edition in groups.items():
        lemma_entries: list[Entry] = []
        for edition in sorted(by_edition):
            items = by_edition[edition]
            if language == SERBO_CROATIAN:
                items = _one_script(items, _is_cyrillic(typed))
            items.sort(
                key=lambda item: (
                    not item[1].in_user_language,
                    item[1].pos == "name",
                    item[1].word != wanted,
                    item[0],
                ),
            )
            lemma_entries.extend(entry for _, entry in items)
        # More senses usually means a more common word: "made" is "make" before it is a maggot.
        other_case = all(
            entry.word[:1].isupper() != wanted[:1].isupper() for entry in lemma_entries
        )
        senses = sum(len(entry.senses) for entry in lemma_entries)
        ranked.append((other_case, -senses, lemma, lemma_entries))
    return [entry for *_, lemma_entries in sorted(ranked) for entry in lemma_entries]


def _text(text: str) -> SafeString:
    # The sidebar applies *emphasis* markdown to its HTML; a literal star must not trigger it.
    return mark_safe(escape(text).replace("*", "&#42;"))  # noqa: S308


def _sense_html(sense: Sense) -> SafeString:
    if sense.note:
        return format_html(
            '{} <span class="wiktionary-note text-muted">({})</span>',
            _text(sense.text),
            _text(sense.note),
        )
    return _text(sense.text)


def _entry_html(entry: Entry) -> SafeString:
    senses = format_html_join(
        "",
        "<li>{}</li>",
        ((_sense_html(sense),) for sense in entry.senses[:MAX_SENSES]),
    )
    return format_html(
        '<div class="wiktionary-entry"><span class="wiktionary-word fw-bold">{}</span> '
        '<span class="wiktionary-pos fst-italic">{}</span>'
        '<ol class="wiktionary-senses mb-1">{}</ol></div>',
        _text(entry.word),
        _text(POS_LABELS.get(entry.pos, entry.pos)),
        senses,
    )


def page_url(entry: Entry) -> str:
    url = f"https://{entry.edition}.wiktionary.org/wiki/{urllib.parse.quote(entry.word)}"
    if entry.edition == ENGLISH_EDITION:
        url += "#" + DATA_LANGUAGE_NAMES[entry.language].replace(" ", "_")
    return url


def render(entries: list[Entry]) -> SafeString:
    return format_html(
        '<div class="wiktionary"><div class="wiktionary-entries">{}</div>'
        '<div class="wiktionary-attribution small text-muted">'
        'from <a href="{}" target="_blank" rel="noopener">Wiktionary</a>, '
        '<a href="{}" target="_blank" rel="noopener">CC BY-SA 4.0</a></div></div>',
        format_html_join("", "{}", ((_entry_html(entry),) for entry in entries)),
        page_url(entries[0]),
        LICENSE_URL,
    )


def summary(entries: list[Entry]) -> str:
    entry = next((entry for entry in entries if entry.in_user_language), entries[0])
    text = entry.senses[0].text
    if entry.edition == RUSSIAN_EDITION:
        text = RUSSIAN_USAGE_LABELS.sub("", text) or text
    # Stress marks help in the sense list; the vocabulary export wants the plain word.
    return text.translate(STRESS_MARKS)
