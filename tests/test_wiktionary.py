import gzip
import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import allure
import httpx
import pytest
from django.conf import settings
from django.core.management import call_command
from django.urls import reverse

from lexiflux.language import wiktionary_import
from lexiflux.language.translation import (
    HtmlTranslation,
    Term,
    Translator,
    TranslatorError,
    WiktionaryTranslator,
)
from lexiflux.language.wiktionary import (
    Entry,
    Sense,
    WiktionaryNotInstalledError,
    lookup,
    lookup_key,
    render,
    serbian_latin,
    summary,
)
from lexiflux.language.wiktionary_import import SOURCES, download, import_wiktionary
from lexiflux.models import Language, LanguagePreferences, LexicalArticle, TranslationHistory

FIXTURES = Path(__file__).parent / "resources" / "wiktionary"
ETAG = '"fixture-1"'


class Kaikki:
    """kaikki.org serving the fixture extracts, gzipped, with ETag and Range support."""

    def __init__(self):
        self.files = {
            source.url: gzip.compress(
                (FIXTURES / source.file_name.removesuffix(".gz")).read_bytes()
            )
            for source in SOURCES
        }
        self.requests: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        body = self.files[str(request.url)]
        headers = {"etag": ETAG}
        if request.headers.get("if-none-match") == ETAG:
            return httpx.Response(304, headers=headers)
        status = 200
        if (range_ := request.headers.get("range")) and request.headers.get("if-range") == ETAG:
            status, body = 206, body[int(range_.removeprefix("bytes=").removesuffix("-")) :]
        headers["content-length"] = str(len(body))
        # A stream, not content: the downloader reads the raw stream.
        return httpx.Response(status, stream=httpx.ByteStream(body), headers=headers)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handle))


def _import(target: Path, tmp_path: Path, **kwargs) -> wiktionary_import.ImportReport:
    return import_wiktionary(
        target,
        tmp_path / "downloads",
        frozenset({"ru"}),
        progress=lambda _message: None,
        client=Kaikki().client(),
        **kwargs,
    )


@pytest.fixture(scope="module")
def data(tmp_path_factory) -> Path:
    tmp_path = tmp_path_factory.mktemp("wiktionary")
    target = tmp_path / "wiktionary.sqlite3"
    _import(target, tmp_path)
    return target


@pytest.fixture
def installed(data):
    with patch.object(settings, "WIKTIONARY_DATABASE", data):
        yield data


def _words(entries):
    return [
        (entry.word, entry.edition, [sense.text for sense in entry.senses]) for entry in entries
    ]


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_import_keeps_the_senses_of_the_six_extracts(tmp_path):
    target = tmp_path / "wiktionary.sqlite3"

    report = _import(target, tmp_path)

    assert report.entries == {
        "ru-en": 2,
        "ru-de": 1,
        "ru-sh": 1,
        "en-en": 12,
        "en-de": 4,
        "en-sh": 6,
    }
    with sqlite3.connect(target) as db:
        assert db.execute(
            "SELECT count(*) FROM entries WHERE word IN ('chat', 'хлеб')"
        ).fetchone() == (0,)
        assert db.execute("SELECT count(*) FROM entries WHERE word = 'steht'").fetchone() == (0,)
    assert report.file_bytes == target.stat().st_size
    assert not (tmp_path / "downloads").exists()
    assert not target.with_name(target.name + ".building").exists()


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_import_replaces_the_old_file_only_when_the_build_succeeds(tmp_path):
    target = tmp_path / "wiktionary.sqlite3"
    target.write_text("old")
    kaikki = Kaikki()
    kaikki.files[SOURCES[1].url] = b"not gzip"

    with pytest.raises(OSError):
        import_wiktionary(
            target,
            tmp_path / "downloads",
            frozenset({"ru"}),
            progress=lambda _message: None,
            client=kaikki.client(),
        )

    assert target.read_text() == "old"
    assert not target.with_name(target.name + ".building").exists()


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_download_resumes_a_partial_file(tmp_path):
    kaikki = Kaikki()
    url = SOURCES[0].url
    target = tmp_path / "ruwiktionary.jsonl.gz"
    target.with_name(target.name + ".part").write_bytes(kaikki.files[url][:10])
    target.with_name(target.name + ".etag").write_text(ETAG)

    with kaikki.client() as client:
        transferred = download(client, url, target, lambda _message: None)

    assert target.read_bytes() == kaikki.files[url]
    assert transferred == len(kaikki.files[url]) - 10
    assert kaikki.requests[0].headers["range"] == "bytes=10-"
    assert not target.with_name(target.name + ".part").exists()


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_kept_downloads_are_reused_while_unchanged(tmp_path):
    kaikki = Kaikki()
    target = tmp_path / "wiktionary.sqlite3"
    import_wiktionary(
        target,
        tmp_path / "downloads",
        frozenset({"ru"}),
        keep_downloads=True,
        progress=lambda _message: None,
        client=kaikki.client(),
    )

    report = import_wiktionary(
        target,
        tmp_path / "downloads",
        frozenset({"ru"}),
        keep_downloads=True,
        progress=lambda _message: None,
        client=kaikki.client(),
    )

    assert report.downloaded_bytes == 0
    assert [request.headers.get("if-none-match") for request in kaikki.requests[-2:]] == [ETAG] * 2
    assert report.entries["en-en"] == 12


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.parametrize(
    "text, language, expected",
    [
        ("Ključa", "sh", "ključa"),
        ("кључа", "sh", "ključa"),
        ("ко̀са", "sh", "kosa"),
        ("kȍse", "sh", "kose"),
        ("ćuprija", "sh", "ćuprija"),
        ("Schlösser", "de", "schlösser"),
        ("Don’t", "en", "don't"),
        ("  made   out ", "en", "made out"),
    ],
)
def test_lookup_key(text, language, expected):
    assert lookup_key(text, language) == expected


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.parametrize(
    "text, language, expected",
    [
        pytest.param(
            "springs",
            "en",
            [
                ("spring", "ru", ["весна", "пружина, рессора"]),
                ("Spring", "ru", ["английская фамилия"]),
                ("spring", "en", ["весна́", "пружи́на, рессо́ра"]),
            ],
            id="en-plural",
        ),
        pytest.param(
            "saw",
            "en",
            [
                ("saw", "en", ["пила́"]),
                ("see", "en", ["ви́деть"]),
            ],
            id="en-own-entry-and-past-tense",
        ),
        pytest.param("made out", "en", [("make out", "en", ["разобра́ть"])], id="en-phrasal-verb"),
        pytest.param(
            "Schlosses",
            "de",
            [
                ("Schloss", "ru", ["замо́к", "за́мок, дворец"]),
                ("Schloss", "en", ["lock (something used for fastening)", "castle"]),
            ],
            id="de-genitive",
        ),
        pytest.param("steht", "de", [("stehen", "en", ["to stand"])], id="de-form-of-entry"),
        pytest.param(
            "reinen Wein einschenken",
            "de",
            [
                (
                    "reinen Wein einschenken",
                    "en",
                    ["to come clean (to tell someone the plain truth)"],
                )
            ],
            id="de-idiom",
        ),
        pytest.param(
            "kosu",
            "sr",
            [
                ("kosa", "en", ["hair (of a person, on the head)", "scythe"]),
                ("kos", "en", ["slant, inclined"]),
            ],
            id="sr-latin-form",
        ),
        pytest.param(
            "косу",
            "sr",
            [
                ("kosa", "en", ["hair (of a person, on the head)", "scythe"]),
                ("kos", "en", ["slant, inclined"]),
            ],
            id="sr-cyrillic-form",
        ),
        pytest.param(
            "кључа",
            "sr",
            [("кључ", "ru", ["ключ"]), ("ključ", "en", ["key", "spanner, wrench"])],
            id="sr-cyrillic-genitive",
        ),
        pytest.param(
            "Ključa",
            "sr",
            [("кључ", "ru", ["ключ"]), ("ključ", "en", ["key", "spanner, wrench"])],
            id="sr-latin-genitive",
        ),
        pytest.param(
            "vratio se",
            "sr",
            [("vratiti se", "en", ["to return, come back"])],
            id="sr-reflexive-verb",
        ),
    ],
)
def test_lookup_finds_the_lemma_of_an_inflected_form(data, text, language, expected):
    assert _words(lookup(text, language, "ru", data)) == expected


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_lookup_ignores_spellings_nobody_prints(data):
    assert [entry.word for entry in lookup("free", "en", "ru", data)] == ["free"]


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_lookup_ignores_the_main_spelling_listed_on_a_variant_page(data):
    assert [entry.word for entry in lookup("bear", "en", "ru", data)] == ["bear"]


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_lookup_ignores_punctuation_around_the_selection(data):
    assert [entry.word for entry in lookup("«Schlosses,", "de", "en", data)] == ["Schloss"]


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_lookup_prefers_the_lemma_written_with_the_same_capital(data):
    assert [entry.word for entry in lookup("Schloss", "de", "en", data)] == ["Schloss", "schließen"]
    assert [entry.word for entry in lookup("schloss", "de", "en", data)] == ["schließen", "Schloss"]


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_lookup_of_a_sentence_start_leads_with_the_common_word(data):
    entries = lookup("Spring", "en", "ru", data)

    assert _words(entries)[:2] == [
        ("spring", "ru", ["весна", "пружина, рессора"]),
        ("Spring", "ru", ["английская фамилия"]),
    ]
    assert summary(entries) == "весна"


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_lookup_ignores_the_words_an_initialism_stands_for(data):
    assert [entry.word for entry in lookup("she", "en", "ru", data)] == ["she"]


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_lookup_puts_the_lemma_with_more_senses_first(data):
    assert [entry.word for entry in lookup("made", "en", "ru", data)] == ["make", "made"]


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_lookup_keeps_a_name_only_when_it_is_the_clicked_word(data):
    assert "Kos" not in [entry.word for entry in lookup("kosu", "sr", "en", data)]
    assert [entry.word for entry in lookup("Kos", "sr", "en", data)] == ["kos", "Kos"]


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_lookup_for_an_english_reader_skips_the_russian_edition(data):
    assert _words(lookup("Schlösser", "de", "en", data)) == [
        ("Schloss", "en", ["lock (something used for fastening)", "castle"]),
    ]


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_lookup_of_a_missing_word_is_empty(data):
    assert lookup("nonexistent", "en", "ru", data) == []


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_lookup_without_the_data_file_says_not_installed(tmp_path):
    with pytest.raises(WiktionaryNotInstalledError):
        lookup("spring", "en", "ru", tmp_path / "missing.sqlite3")


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_render_escapes_dictionary_text_and_credits_wiktionary(data):
    entries = lookup("free", "en", "ru", data)

    html = render(entries)

    assert "Not imprisoned &lt;or&gt; &#42;enslaved&#42;." in html
    assert "<or>" not in html
    assert 'from <a href="https://en.wiktionary.org/wiki/free#English"' in html
    assert '>Wiktionary</a>, <a href="https://creativecommons.org/licenses/by-sa/4.0/"' in html
    assert "CC BY-SA 4.0</a>" in html
    assert "\n" not in html


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_render_shows_translations_with_their_sense(data):
    html = render(lookup("spring", "en", "ru", data))

    assert '<li>весна́ <span class="wiktionary-note text-muted">(season)</span></li>' in html
    assert html.index("весна</li>") < html.index("весна́ <span")


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_summary_prefers_a_user_language_sense(data):
    assert summary(lookup("Schlösser", "de", "ru", data)) == "замок"
    assert summary(lookup("kosu", "sr", "ru", data)) == "hair (of a person, on the head)"


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.parametrize(
    "edition, sense, expected",
    [
        ("ru", "экон. делать, изготовлять", "делать, изготовлять"),
        ("ru", "матем., геометр. трёхсторонний", "трёхсторонний"),
        ("ru", "с.-х. насест", "насест"),
        ("ru", "сокр. от as soon as possible", "сокр. от as soon as possible"),
        ("ru", "биохим. сокр. от NADH", "сокр. от NADH"),
        ("ru", "исч. и неисч. вода", "вода"),
        ("ru", "устар. или поэт. истина", "истина"),
        ("ru", "мн. ч. клещи", "клещи"),
        ("ru", "мн. ч. от zipper", "мн. ч. от zipper"),
        ("ru", "т. е.", "т. е."),
        ("ru", "весна", "весна"),
        ("en", "abbr. of something", "abbr. of something"),
    ],
)
def test_summary_drops_the_usage_labels_of_russian_senses(edition, sense, expected):
    entry = Entry("make", "verb", edition, "en", (Sense(sense), Sense("экон. марка")), True)

    assert summary([entry]) == expected
    assert "экон. марка" in render([entry])


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_summary_drops_the_stress_marks_the_sense_list_keeps():
    entry = Entry("spring", "noun", "en", "en", (Sense("весна́, по̀лдень", "season"),), True)

    assert summary([entry]) == "весна, полдень"
    assert "весна́, по̀лдень" in render([entry])


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_serbian_latin_keeps_the_case():
    assert serbian_latin("Љубав, ЊЕГОШ и кућа; Ljubav") == "Ljubav, NjEGOŠ i kuća; Ljubav"


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_wiktionary_translator_returns_trusted_html(installed):
    result = Translator("Wiktionary", "German", "Russian").translate(Term("Schlosses"))

    assert isinstance(result, HtmlTranslation)
    assert result.translation == "замок"
    assert result.html.startswith('<div class="wiktionary">')


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.parametrize(
    "source, word, kind",
    [
        ("english", "nonexistent", TranslatorError.NOT_FOUND),
        ("french", "chat", TranslatorError.UNSUPPORTED),
    ],
)
def test_wiktionary_translator_failures(installed, source, word, kind):
    with pytest.raises(TranslatorError) as error:
        WiktionaryTranslator(source, "russian").translate(Term(word))

    assert error.value.kind == kind


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_wiktionary_translator_without_data_is_not_installed(tmp_path):
    with (
        patch.object(settings, "WIKTIONARY_DATABASE", tmp_path / "missing.sqlite3"),
        pytest.raises(TranslatorError) as error,
    ):
        WiktionaryTranslator("english", "russian").translate(Term("spring"))

    assert error.value.kind == TranslatorError.NOT_INSTALLED


def _preferences(user, book, dictionary="Wiktionary"):
    preferences = LanguagePreferences.get_or_create_language_preferences(
        user=user, language=book.language
    )
    preferences.user_language = Language.objects.get(name="Russian")
    preferences.inline_translation_type = "Dictionary"
    preferences.inline_translation_parameters = {"dictionary": dictionary}
    preferences.save()
    return preferences


def _page(book, content):
    page = book.pages.get(number=1)
    page.content = content
    page.save()


def _popup(client, user, book, word_id="2"):
    client.force_login(user)
    _preferences(user, book)
    return client.get(
        reverse("translate"),
        {
            "lexical-article": "0",
            "book-code": book.code,
            "book-page-number": "1",
            "word-ids": word_id,
        },
    )


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.django_db
def test_popup_shows_the_sense_list_and_remembers_the_first_sense(installed, client, user, book):
    _page(book, "Early springs came.")

    response = _popup(client, user, book, word_id="1")

    data = response.json()
    assert data["html"] is True
    assert "error" not in data
    assert data["article"].startswith('<div class="wiktionary">')
    assert "CC BY-SA 4.0" in data["article"]
    assert TranslationHistory.objects.get(user=user).translation == "весна"


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.django_db
def test_popup_without_data_shows_the_import_command(client, user, book, tmp_path):
    with patch.object(settings, "WIKTIONARY_DATABASE", tmp_path / "missing.sqlite3"):
        response = _popup(client, user, book)

    data = response.json()
    assert data["error"] is True
    assert "Wiktionary data is not installed." in data["article"]
    assert "<code>./manage import-wiktionary</code>" in data["article"]
    assert not TranslationHistory.objects.filter(user=user).exists()


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.django_db
def test_popup_for_a_missing_entry_is_an_alert(installed, client, user, book):
    response = _popup(client, user, book)

    data = response.json()
    assert data["error"] is True
    assert "Wiktionary found no translation." in data["article"]


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.django_db
def test_sidebar_article_is_the_sense_list_unescaped(installed, client, user, book):
    _page(book, "Early springs came.")
    client.force_login(user)
    LexicalArticle.objects.create(
        language_preferences=_preferences(user, book, "Google"),
        type="Dictionary",
        title="Wiktionary",
        parameters={"dictionary": "Wiktionary"},
        order=10,
    )

    response = client.get(
        reverse("translate_stream"),
        {"lexical-article": "5", "book-code": book.code, "book-page-number": "1", "word-ids": "1"},
    )
    events = [json.loads(line) for line in b"".join(response.streaming_content).splitlines()]

    assert [event["event"] for event in events] == ["delta", "done"]
    assert events[0]["text"].startswith('<div class="wiktionary">')
    assert "<li>весна</li>" in events[0]["text"]


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.django_db
def test_import_command_keeps_translations_for_the_configured_user_languages(user, book, tmp_path):
    preferences = _preferences(user, book)
    preferences.user_language = Language.objects.get(name="German")
    preferences.save()
    target = tmp_path / "wiktionary.sqlite3"
    out = tmp_path / "out.txt"

    with (
        patch.object(settings, "WIKTIONARY_DATABASE", target),
        patch.object(wiktionary_import, "http_client", Kaikki().client),
        out.open("w") as stdout,
    ):
        call_command("import-wiktionary", stdout=stdout)

    assert "Wiktionary imported" in out.read_text()
    assert _words(lookup("springs", "en", "de", target)) == [("spring", "en", ["Frühling"])]
    assert _words(lookup("springs", "en", "ru", target))[-1] == (
        "spring",
        "en",
        ["весна́", "пружи́на, рессо́ра"],
    )
    assert not (tmp_path / "wiktionary-downloads").exists()


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.django_db
def test_serbian_and_croatian_readers_get_the_serbo_croatian_translations(user, book, tmp_path):
    preferences = _preferences(user, book)
    preferences.user_language = Language.objects.get(name="Serbian")
    preferences.save()
    target = tmp_path / "wiktionary.sqlite3"

    with (
        patch.object(settings, "WIKTIONARY_DATABASE", target),
        patch.object(wiktionary_import, "http_client", Kaikki().client),
        (tmp_path / "out.txt").open("w") as stdout,
    ):
        call_command("import-wiktionary", stdout=stdout)

    for user_language in ("sr", "hr", "bs"):
        assert _words(lookup("springs", "en", user_language, target)) == [
            ("spring", "en", ["proljeće"]),
        ]
