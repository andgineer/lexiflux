import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch

import allure
import httpx
import pytest
from django.urls import reverse
from django.utils import timezone

from lexiflux.language import wiktionary
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
    WiktionaryUnreachableError,
    _strip_accents,
    http_client,
    kaikki_url,
    lookup,
    lookup_key,
    render,
    sentence_start,
    serbian_cyrillic,
    serbian_latin,
    summary,
)
from lexiflux.models import (
    Language,
    LanguagePreferences,
    LexicalArticle,
    TranslationHistory,
    WiktionaryPage,
)
from tests.kaikki import Kaikki

EN = "dictionary/English"
RU = "ruwiktionary/Английский"
SPRINGS_PAGES = [f"{EN}/spring", f"{EN}/springs", f"{RU}/spring", f"{RU}/springs"]
KING_IN_MANDARIN = ["國王 /国王, 王", "王, 國王 /国王", "K (kei, kǎi), 老K, 凱 /凯", "王", "王"]


@pytest.fixture
def kaikki(db):
    fake = Kaikki()
    with patch.object(wiktionary, "http_client", fake.client):
        yield fake


def _words(entries):
    return [
        (entry.word, entry.edition, [sense.text for sense in entry.senses]) for entry in entries
    ]


def _heads(entries):
    return [(entry.word, entry.pos, entry.edition) for entry in entries]


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.parametrize(
    "edition, language, word, url",
    [
        ("en", "en", "spring", "https://kaikki.org/dictionary/English/meaning/s/sp/spring.jsonl"),
        ("en", "en", "a", "https://kaikki.org/dictionary/English/meaning/a/a/a.jsonl"),
        ("en", "en", "I", "https://kaikki.org/dictionary/English/meaning/I/I/I.jsonl"),
        ("en", "en", "I'm", "https://kaikki.org/dictionary/English/meaning/I/I%27/I%27m.jsonl"),
        (
            "en",
            "en",
            "at any rate",
            "https://kaikki.org/dictionary/English/meaning/a/at/at%20any%20rate.jsonl",
        ),
        (
            "en",
            "de",
            "z. B.",
            "https://kaikki.org/dictionary/German/meaning/z/z_/z_dot_%20B_dot_.jsonl",
        ),
        (
            "en",
            "en",
            "AC/DC",
            "https://kaikki.org/dictionary/English/meaning/A/AC/AC_slash_DC.jsonl",
        ),
        (
            "en",
            "sh",
            "ključ",
            "https://kaikki.org/dictionary/Serbo-Croatian/meaning/k/kl/klju%C4%8D.jsonl",
        ),
        (
            "ru",
            "sh",
            "кључ",
            "https://kaikki.org/ruwiktionary/%D0%A1%D0%B5%D1%80%D0%B1%D1%81%D0%BA%D0%B8%D0%B9"
            "/meaning/%D0%BA/%D0%BA%D1%99/%D0%BA%D1%99%D1%83%D1%87.jsonl",
        ),
        (
            "ru",
            "de",
            "Schloss",
            "https://kaikki.org/ruwiktionary/%D0%9D%D0%B5%D0%BC%D0%B5%D1%86%D0%BA%D0%B8%D0%B9"
            "/meaning/S/Sc/Schloss.jsonl",
        ),
        (
            "ru",
            "hr",
            "mlijeko",
            "https://kaikki.org/ruwiktionary/%D0%A5%D0%BE%D1%80%D0%B2%D0%B0%D1%82%D1%81%D0%BA%D0%B8%D0%B9"
            "/meaning/m/ml/mlijeko.jsonl",
        ),
    ],
)
def test_kaikki_url_escapes_the_page_name(edition, language, word, url):
    assert kaikki_url(edition, language, word) == url


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
    "text, expected",
    [
        ("Ćerka", "Ćerka"),
        ("ćerka", "ćerka"),
        ("Čovek", "Čovek"),
        ("kȍsu", "kosu"),
        ("čćđšž ČĆĐŠŽ", "čćđšž ČĆĐŠŽ"),
        ("ȍ ú à ȁ ŕ Ú Ȁ", "o u a a r U A"),
    ],
)
def test_strip_accents_keeps_serbian_letters_and_drops_pitch_accents(text, expected):
    assert _strip_accents(text) == expected


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_serbian_transliteration_keeps_the_case_both_ways():
    assert serbian_latin("Љубав, ЊЕГОШ и кућа; Ljubav") == "Ljubav, NjEGOŠ i kuća; Ljubav"
    assert serbian_cyrillic("Ljubav, NJEGOŠ, Džep i đak") == "Љубав, ЊЕГОШ, Џеп и ђак"
    assert serbian_cyrillic(serbian_latin("Ђурђевдан у Љубљани")) == "Ђурђевдан у Љубљани"


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.parametrize(
    "text, language, expected",
    [
        pytest.param(
            "springs",
            "en",
            [
                ("spring", "ru", ["весна", "источник, ключ, родник", "пружина, рессора"]),
                (
                    "spring",
                    "ru",
                    ["появляться (появиться)", "прыгать (прыгнуть), скакать (скакнуть)"],
                ),
            ],
            id="en-plural",
        ),
        pytest.param(
            "Träumen",
            "de",
            [
                ("Traum", "ru", ["сновидение, сон", "мечта, грёза", "мечта, иллюзия"]),
                ("Traum", "en", ["dream"]),
            ],
            id="de-dative-plural",
        ),
        pytest.param(
            "kosu",
            "sr",
            [
                ("коса", "ru", ["коса I", "с.-х. коса II"]),
                ("kosa", "en", ["hair (of a person, on the head)"]),
            ],
            id="sr-latin-form",
        ),
        pytest.param(
            "косу",
            "sr",
            [
                ("коса", "ru", ["коса I", "с.-х. коса II"]),
                ("kosa", "en", ["hair (of a person, on the head)"]),
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
    ],
)
def test_lookup_finds_the_lemma_of_an_inflected_form(kaikki, text, language, expected):
    assert _words(lookup(text, language, "ru"))[:2] == expected


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_serbian_pages_are_latin_in_the_english_edition_and_cyrillic_in_the_russian(kaikki):
    lookup("кључа", "sr", "ru")

    assert sorted(kaikki.requested()) == [
        "dictionary/Serbo-Croatian/ključ",
        "dictionary/Serbo-Croatian/ključa",
        "ruwiktionary/Сербский/кључ",
        "ruwiktionary/Сербский/кључа",
    ]


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_russian_reader_gets_both_editions_russian_first(kaikki):
    entries = lookup("springs", "en", "ru")

    assert sorted(kaikki.requested()) == SPRINGS_PAGES
    assert [entry.edition for entry in entries] == ["ru", "ru", "en", "en", "en"]
    assert summary(entries) == "весна"


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_other_readers_get_the_english_edition_with_their_translations(kaikki):
    entries = lookup("springs", "en", "de")

    assert sorted(kaikki.requested()) == [f"{EN}/spring", f"{EN}/springs"]
    assert _words(entries)[0][2][:2] == [
        "Frühling, Frühjahr, (dated)/(poetic) Lenz, Frühlingszeit, Frühjahrszeit, Früelig",
        "Quelle",
    ]
    assert {entry.edition for entry in entries} == {"en"}


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.parametrize("user_language", ["sr", "hr", "bs"])
def test_serbian_croatian_and_bosnian_readers_get_the_serbo_croatian_translations(
    kaikki, user_language
):
    entries = lookup("springs", "en", user_language)

    assert entries[0].senses[1] == Sense("ѝзвор, ìzvor", "water springing from the ground")


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.parametrize(
    "word, user_language, expected",
    [
        ("springs", "no", ["vår", "kilde", "fjær, fjør"]),
        ("springs", "fil", ["tagsibol", "bukal, batis", "muwelye, paigkas, kuwerdas"]),
        ("springs", "ku", ["bihar", "kanî, kehnî"]),
        ("king", "zh-CN", KING_IN_MANDARIN),
    ],
)
def test_readers_get_translations_filed_under_other_codes(kaikki, word, user_language, expected):
    entries = lookup(word, "en", user_language)

    assert [sense.text for sense in entries[0].senses] == expected


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_croatian_books_use_the_russian_editions_croatian_section_in_latin(kaikki):
    entries = lookup("mlijeko", "hr", "ru")

    assert sorted(kaikki.requested()) == [
        "dictionary/Serbo-Croatian/mlijeko",
        "ruwiktionary/Хорватский/mlijeko",
    ]
    assert _words(entries) == [("mlijeko", "ru", ["молоко"]), ("mlijeko", "en", ["milk"])]


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_bosnian_books_use_the_russian_editions_serbian_section(kaikki):
    entries = lookup("mlijeko", "bs", "ru")

    assert sorted(kaikki.requested()) == [
        "dictionary/Serbo-Croatian/mlijeko",
        "ruwiktionary/Сербский/млијеко",
    ]
    assert _words(entries) == [("mlijeko", "en", ["milk"])]


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_english_reader_gets_english_definitions(kaikki):
    entries = lookup("Träumen", "de", "en")

    assert _words(entries) == [("Traum", "en", ["dream"])]
    assert summary(entries) == "dream"


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.parametrize(
    "text, expected",
    [
        pytest.param(
            "I'm",
            [("I'm", "contraction", "en"), ("I", "pron", "ru"), ("I", "pron", "en")],
            id="contraction",
        ),
        pytest.param(
            "you're",
            [("you're", "contraction", "en"), ("you", "pron", "ru"), ("you", "pron", "en")],
            id="contraction-not-its-misspelling-link",
        ),
        pytest.param(
            "'tis",
            [("'tis", "contraction", "en"), ("it", "pron", "ru"), ("it", "pron", "en")],
            id="archaic-contraction",
        ),
        pytest.param(
            "liveth",
            [("liveth", "verb", "en"), ("live", "verb", "ru"), ("live", "adj", "ru")],
            id="archaic-inflection",
        ),
        pytest.param(
            "wouldst",
            [("wouldst", "verb", "en"), ("will", "verb", "ru"), ("will", "verb", "ru")],
            id="archaic-past",
        ),
        pytest.param(
            "Curiouser",
            [("curiouser", "adj", "en"), ("curious", "adj", "ru"), ("curious", "adj", "en")],
            id="nonstandard-comparative",
        ),
    ],
)
def test_a_form_the_lemmatiser_keeps_follows_its_form_of_link(kaikki, text, expected):
    entries = lookup(text, "en", "ru")

    assert _heads(entries)[:3] == expected
    assert len(kaikki.requested()) == 4


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_the_followed_lemma_comes_after_the_words_own_senses_and_its_form_of_line(kaikki):
    entries = lookup("I'm", "en", "ru")

    assert _words(entries)[0] == ("I'm", "en", ["Contraction of I + am."])
    assert summary(entries) == "я"
    html = render(entries)
    assert html.index("Contraction of I + am.") < html.index("я</li>")


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.parametrize("word", ["she", "be"])
def test_a_word_with_its_own_entries_leads_with_them(kaikki, word):
    entries = lookup(word, "en", "ru")

    assert {entry.word for entry in entries} == {word}
    assert sorted(kaikki.requested()) == [f"{EN}/{word}", f"{RU}/{word}"]


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.parametrize(
    "passage, expected",
    [
        ("⟦Ich⟧ war da.", True),
        ("Er kam nach Hause. ⟦Ich⟧ war da.", True),
        ("Wirklich?! ⟦Nein⟧.", True),
        ("Er wartete… ⟦Dann⟧ ging er.", True),
        ("Er sagte: „⟦Aber⟧ nein!“", True),
        ("“Off with her head!” — ⟦She⟧ ran.", True),
        ("We flew to ⟦China⟧ last year.", False),
        ("said the ⟦King⟧, “and", False),
        ("1914 ⟦March⟧", False),
        ("", None),
        ("a passage without a mark", None),
    ],
)
def test_sentence_start_is_read_from_the_marked_passage(passage, expected):
    assert sentence_start(passage) is expected


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.parametrize(
    "passage, head, expected",
    [
        pytest.param("We flew to ⟦China⟧ last year.", ("China", "noun", "ru"), "Китай", id="China"),
        pytest.param("She came in ⟦May⟧ this year.", ("May", "noun", "ru"), "май", id="May"),
        pytest.param("It rained in ⟦March⟧.", ("March", "noun", "ru"), "март", id="March"),
        pytest.param(
            "We went to ⟦Turkey⟧ in June.", ("Turkey", "noun", "ru"), "Турция", id="Turkey"
        ),
    ],
)
def test_an_english_capital_in_mid_sentence_leads_with_the_name(kaikki, passage, head, expected):
    word = head[0]

    entries = lookup(word, "en", "ru", passage)

    assert sorted(kaikki.requested()) == sorted(
        f"{edition}/{page}" for edition in (EN, RU) for page in (word, word.lower())
    )
    assert _heads(entries)[0] == head
    assert word.lower() in {entry.word for entry in entries}
    assert summary(entries) == expected


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.parametrize(
    "word, passage, head",
    [
        pytest.param("China", "⟦China⟧ is far away.", ("china", "noun", "ru"), id="China"),
        pytest.param("May", "⟦May⟧ I come in?", ("may", "verb", "ru"), id="May"),
        pytest.param("March", "“⟦March⟧!”", ("march", "noun", "ru"), id="March"),
        pytest.param("China", "", ("china", "noun", "ru"), id="no-passage"),
    ],
)
def test_an_english_capital_at_a_sentence_start_is_the_lowercase_word(kaikki, word, passage, head):
    entries = lookup(word, "en", "ru", passage)

    assert all(path.rsplit("/", 1)[1].islower() for path in kaikki.requested())
    assert _heads(entries)[0] == head


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_an_english_name_without_translations_follows_the_lowercase_word(kaikki):
    entries = lookup("King", "en", "ru", "“Off with his head!” said the ⟦King⟧.")

    assert _heads(entries)[0] == ("king", "noun", "ru")
    assert ("King", "name", "en") in _heads(entries)
    assert summary(entries).startswith("король")


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_a_serbian_capital_in_mid_sentence_leads_with_the_name(kaikki):
    entries = lookup("Luka", "sr", "ru", "Juče je ⟦Luka⟧ došao.")

    assert _heads(entries)[:2] == [("Лука", "noun", "ru"), ("Luka", "name", "en")]
    assert "luka" in {entry.word for entry in entries}


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_a_sentence_start_is_the_common_word_not_a_surname(kaikki):
    entries = lookup("Still", "en", "ru")

    assert {entry.word for entry in entries} == {"still"}
    assert "name" not in {entry.pos for entry in entries}
    assert ("still", "adv", "ru") in _heads(entries)
    assert summary(entries) == "тихий, бесшумный, безмолвный"


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_a_form_with_its_own_lemma_does_not_follow_links(kaikki):
    entries = lookup("made", "en", "ru")

    assert [entry.word for entry in entries][:3] == ["make", "make", "make"]
    assert len(kaikki.requested()) == 4


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_at_most_three_links_are_followed(kaikki):
    targets = ["spring", "be", "she", "live"]
    page = {
        "word": "xyzzy",
        "pos": "verb",
        "senses": [
            {"glosses": [f"form of {target}"], "tags": ["form-of"], "form_of": [{"word": target}]}
            for target in targets
        ],
    }
    kaikki.pages[kaikki_url("en", "en", "xyzzy")] = json.dumps(page)

    entries = lookup("xyzzy", "en", "en")

    assert sorted(kaikki.requested()) == [f"{EN}/be", f"{EN}/she", f"{EN}/spring", f"{EN}/xyzzy"]
    assert entries[0] == Entry(
        "xyzzy",
        "verb",
        "en",
        "en",
        tuple(Sense(f"form of {target}") for target in targets),
        in_user_language=False,
    )


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_a_name_is_looked_up_as_written_when_nothing_matches_it_in_lower_case(kaikki):
    entries = lookup("London", "en", "ru")

    assert _heads(entries) == [("London", "noun", "ru"), ("London", "name", "en")]
    assert summary(entries) == "Лондон (город в Великобритании)"


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.parametrize(
    "text, pages, expected",
    [
        pytest.param("robin", ["robin"], "малиновка, зарянка (Erithacus rubecola)", id="lowercase"),
        pytest.param("august", ["august"], "августовский", id="lowercase-adjective"),
        pytest.param("Robin", ["Robin"], "Робин; английское имя", id="capitalised"),
    ],
)
def test_a_lowercase_word_is_not_the_name_the_lemmatiser_capitalises(kaikki, text, pages, expected):
    entries = lookup(text, "en", "ru")

    assert sorted(kaikki.requested()) == [f"{EN}/{page}" for page in pages] + [
        f"{RU}/{page}" for page in pages
    ]
    assert summary(entries) == expected


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.parametrize(
    "text, language, user_language, expected",
    [
        pytest.param(
            "Beogradu",
            "sr",
            "en",
            [("Beograd", "name", "en")],
            id="sr-locative",
        ),
        pytest.param("Evrope", "sr", "ru", [("Evropa", "name", "en")], id="sr-genitive"),
        pytest.param(
            "Deutschlands",
            "de",
            "en",
            [("Deutschland", "name", "en")],
            id="de-genitive",
        ),
        pytest.param(
            "Deutschlands",
            "de",
            "ru",
            [("Deutschland", "noun", "ru")],
            id="de-genitive-name-left-out-when-something-else-is-found",
        ),
    ],
)
def test_an_inflected_name_shows_its_lemmas_name_when_nothing_else_is_found(
    kaikki, text, language, user_language, expected
):
    assert _heads(lookup(text, language, user_language)) == expected


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.parametrize(
    "text, user_language, expected",
    [
        pytest.param(
            "Tanzen",
            "ru",
            [
                ("Tanzen", "en", "gerund of tanzen"),
                ("tanzen", "ru", "танцевать, плясать"),
                ("tanzen", "en", "to dance"),
            ],
            id="russian-reader",
        ),
        pytest.param(
            "Gehen",
            "en",
            [("Gehen", "en", 'gerund of gehen: "going"'), ("gehen", "en", "to go, to walk")],
            id="english-reader",
        ),
    ],
)
def test_a_german_nominalised_infinitive_follows_its_link_to_the_verb(
    kaikki, text, user_language, expected
):
    entries = lookup(text, "de", user_language)

    assert [(word, edition, senses[0]) for word, edition, senses in _words(entries)] == expected


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_accents_printed_on_a_serbian_word_are_dropped(kaikki):
    entries = lookup("kȍsu", "sr", "ru")

    assert sorted(kaikki.requested()) == [
        "dictionary/Serbo-Croatian/kosa",
        "dictionary/Serbo-Croatian/kosu",
        "ruwiktionary/Сербский/коса",
        "ruwiktionary/Сербский/косу",
    ]
    assert _words(entries)[:2] == [
        ("коса", "ru", ["коса I", "с.-х. коса II"]),
        ("kosa", "en", ["hair (of a person, on the head)"]),
    ]


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_a_capital_c_with_acute_keeps_its_accent(kaikki):
    lookup("Ćerka", "sr", "ru")

    assert "dictionary/Serbo-Croatian/ćerka" in kaikki.requested()
    assert not any(path.endswith("/cerka") for path in kaikki.requested())


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_a_capitalised_german_word_with_only_names_is_also_looked_up_in_lower_case(kaikki):
    entries = lookup("Schön", "de", "ru")

    assert sorted(kaikki.requested()) == [
        "dictionary/German/Schön",
        "dictionary/German/schön",
        "ruwiktionary/Немецкий/Schön",
        "ruwiktionary/Немецкий/schön",
    ]
    assert _heads(entries)[:3] == [
        ("schön", "adj", "ru"),
        ("schön", "adv", "ru"),
        ("schön", "adj", "en"),
    ]
    assert _heads(entries)[-1] == ("Schön", "name", "en")
    assert summary(entries) == "красивый, прекрасный"


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.parametrize("word", ["Schloss", "Bank", "Gut"])
@pytest.mark.parametrize("passage", ["", "Er sah das ⟦{}⟧ am See."], ids=["no-passage", "mid"])
def test_a_capitalised_german_noun_is_not_looked_up_in_lower_case(kaikki, word, passage):
    entries = lookup(word, "de", "ru", passage.format(word))

    assert all(path.rsplit("/", 1)[1][0].isupper() for path in kaikki.requested())
    assert _heads(entries)[0] == (word, "noun", "ru")


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.parametrize(
    "passage, expected",
    [
        pytest.param("Er kam nach Hause. ⟦Ich⟧ war schon da.", "я", id="Ich"),
        pytest.param("Das war gut. ⟦Aber⟧ dann kam er.", "но", id="Aber"),
        pytest.param("⟦Nichts⟧ war mehr wie früher.", "ничего", id="Nichts"),
        pytest.param("⟦Es⟧ war kein Traum.", "(личное местоимение) оно", id="Es"),
        pytest.param("⟦Wenn⟧ er kommt, gehen wir.", "когда", id="Wenn"),
    ],
)
def test_a_german_capital_at_a_sentence_start_leads_with_its_lowercase_lemma(
    kaikki, passage, expected
):
    word = passage.split("⟦")[1].split("⟧")[0]

    entries = lookup(word, "de", "ru", passage)

    assert len(kaikki.requests) <= 4
    assert entries[0].word == word.lower()
    assert word in {entry.word for entry in entries}
    assert summary(entries) == expected


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.parametrize("passage", ["Das ⟦Ich⟧ ist eine Instanz der Psyche.", ""])
def test_a_german_capital_in_mid_sentence_keeps_the_noun_first(kaikki, passage):
    entries = lookup("Ich", "de", "ru", passage)

    assert _heads(entries)[0] == ("Ich", "noun", "ru")
    assert summary(entries) == "«я», моя личность"


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_a_german_noun_at_a_sentence_start_is_also_looked_up_in_lower_case(kaikki):
    entries = lookup("Gut", "de", "ru", "⟦Gut⟧, dass du da bist.")

    assert sorted(kaikki.requested()) == [
        "dictionary/German/Gut",
        "dictionary/German/gut",
        "ruwiktionary/Немецкий/Gut",
        "ruwiktionary/Немецкий/gut",
    ]
    assert _heads(entries)[:2] == [("gut", "adj", "ru"), ("gut", "adv", "ru")]
    assert ("Gut", "noun", "ru") in _heads(entries)
    assert summary(entries) == "хороший, добрый, качественный"


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_a_german_noun_at_a_sentence_start_leads_when_its_lowercase_is_only_a_form(kaikki):
    entries = lookup("Schloss", "de", "ru", "⟦Schloss⟧ Neuschwanstein liegt in Bayern.")

    assert _heads(entries)[0] == ("Schloss", "noun", "ru")
    assert ("schließen", "verb", "ru") in _heads(entries)
    assert summary(entries) == "замок"


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_lookup_ignores_punctuation_around_the_selection(kaikki):
    assert {entry.word for entry in lookup("«Schloss,»", "de", "en")} == {"Schloss"}


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_lookup_of_a_missing_word_is_empty(kaikki):
    assert lookup("nonexistent", "en", "ru") == []


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_a_selection_longer_than_any_title_requests_nothing(kaikki):
    assert lookup("word " * 60, "en", "ru") == []
    assert kaikki.requests == []


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_pages_and_missing_pages_are_cached(kaikki):
    first = lookup("springs", "en", "ru")
    requested = len(kaikki.requests)

    assert lookup("springs", "en", "ru") == first
    assert len(kaikki.requests) == requested
    missing = WiktionaryPage.objects.get(url=kaikki_url("ru", "en", "springs"), user_language="ru")
    assert missing.content is None
    assert WiktionaryPage.objects.filter(content__isnull=False).count() == 3


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_the_cache_keeps_the_translations_of_one_user_language(kaikki):
    lookup("springs", "en", "ru")

    entries = lookup("springs", "en", "de")

    assert entries[0].senses[1].text == "Quelle"


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_pages_older_than_thirty_days_are_fetched_again(kaikki):
    lookup("springs", "en", "ru")
    WiktionaryPage.objects.update(fetched=timezone.now() - timedelta(days=31))
    kaikki.requests.clear()

    lookup("springs", "en", "ru")

    assert sorted(kaikki.requested()) == SPRINGS_PAGES
    assert (
        WiktionaryPage.objects.filter(fetched__lt=timezone.now() - timedelta(days=1)).count() == 0
    )


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.parametrize(
    "failure",
    [
        pytest.param(503, id="5xx"),
        pytest.param(429, id="rate-limit"),
        pytest.param(httpx.ConnectError("refused"), id="connection"),
        pytest.param(httpx.ReadTimeout("slow"), id="timeout"),
    ],
)
def test_one_edition_failing_shows_the_other_and_caches_nothing_for_it(kaikki, failure):
    kaikki.fail("/ruwiktionary/", failure)

    entries = lookup("springs", "en", "ru")

    assert {entry.edition for entry in entries} == {"en"}
    assert not WiktionaryPage.objects.filter(url__contains="/ruwiktionary/").exists()
    kaikki.failures.clear()
    kaikki.requests.clear()
    assert lookup("springs", "en", "ru")[0].edition == "ru"
    assert sorted(kaikki.requested()) == [f"{RU}/spring", f"{RU}/springs"]


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_everything_failing_is_unreachable_and_not_cached(kaikki):
    kaikki.fail("kaikki.org", 503)

    with pytest.raises(WiktionaryUnreachableError):
        lookup("springs", "en", "ru")

    assert not WiktionaryPage.objects.exists()


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_missing_pages_and_a_failure_without_entries_is_unreachable(kaikki):
    kaikki.fail("/ruwiktionary/", httpx.ConnectError("refused"))

    with pytest.raises(WiktionaryUnreachableError):
        lookup("nonexistent", "en", "ru")

    assert list(WiktionaryPage.objects.values_list("content", flat=True)) == [None]


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_a_page_that_is_not_json_lines_is_a_failure(kaikki):
    kaikki.pages[kaikki_url("en", "en", "nonexistent")] = "<html>moved</html>"

    with pytest.raises(WiktionaryUnreachableError):
        lookup("nonexistent", "en", "en")

    assert not WiktionaryPage.objects.exists()


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_a_record_of_another_shape_fails_only_its_page(kaikki):
    kaikki.pages[kaikki_url("ru", "en", "spring")] = json.dumps(
        {"word": "spring", "pos": "noun", "senses": None}
    )

    entries = lookup("springs", "en", "ru")

    assert {entry.edition for entry in entries} == {"en"}
    assert sorted(WiktionaryPage.objects.values_list("url", flat=True)) == [
        kaikki_url("en", "en", "spring"),
        kaikki_url("en", "en", "springs"),
        kaikki_url("ru", "en", "springs"),
    ]


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_requests_still_queued_at_the_deadline_are_not_sent(kaikki):
    stall = threading.Event()

    def stalled(request: httpx.Request) -> httpx.Response:
        kaikki.requests.append(str(request.url))
        stall.wait(5)
        return httpx.Response(404)

    kaikki.handle = stalled
    one_thread = ThreadPoolExecutor(max_workers=1)
    try:
        with (
            patch.object(wiktionary, "_fetchers", one_thread),
            patch.object(wiktionary, "LOOKUP_SECONDS", 0.3),
            pytest.raises(WiktionaryUnreachableError),
        ):
            lookup("she", "en", "ru")
    finally:
        stall.set()
        one_thread.shutdown(wait=True)

    assert len(kaikki.requests) == 1


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_a_stalled_kaikki_is_abandoned_at_the_deadline(kaikki):
    stall = threading.Event()

    def stalled(request: httpx.Request) -> httpx.Response:
        stall.wait(5)
        return httpx.Response(200, text=kaikki.pages[str(request.url)])

    kaikki.handle = stalled
    started = time.monotonic()
    try:
        with (
            patch.object(wiktionary, "LOOKUP_SECONDS", 0.3),
            pytest.raises(WiktionaryUnreachableError),
        ):
            lookup("she", "en", "ru")
    finally:
        stall.set()

    assert time.monotonic() - started < 1.5
    assert not WiktionaryPage.objects.exists()


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_kaikki_requests_name_lexiflux_and_give_up_after_two_seconds(kaikki):
    timeouts = []
    serve = kaikki.handle

    def timed(request: httpx.Request) -> httpx.Response:
        timeouts.append(request.extensions["timeout"])
        return serve(request)

    kaikki.handle = timed

    lookup("springs", "en", "ru")

    assert http_client().headers["User-Agent"] == "lexiflux (https://github.com/andgineer/lexiflux)"
    assert len(timeouts) == 4
    assert all(0 < seconds <= 2.0 for timeout in timeouts for seconds in timeout.values())


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_render_escapes_dictionary_text_and_credits_wiktionary():
    entries = [Entry("free", "adj", "en", "en", (Sense("Not imprisoned <or> *enslaved*."),), True)]

    html = render(entries)

    assert "Not imprisoned &lt;or&gt; &#42;enslaved&#42;." in html
    assert "<or>" not in html
    assert 'from <a href="https://en.wiktionary.org/wiki/free#English"' in html
    assert '>Wiktionary</a>, <a href="https://creativecommons.org/licenses/by-sa/4.0/"' in html
    assert "CC BY-SA 4.0</a>" in html
    assert "\n" not in html


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_render_shows_translations_with_their_sense_and_links_the_first_entry(kaikki):
    html = render(lookup("springs", "en", "ru"))

    note = '<span class="wiktionary-note text-muted">'
    assert (
        f"<li>весна́ {note}(season between winter and summer in temperate climates)</span>" in html
    )
    assert html.index("<li>весна</li>") < html.index(f"весна́ {note}")
    assert 'from <a href="https://ru.wiktionary.org/wiki/spring"' in html


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
def test_summary_prefers_a_user_language_sense(kaikki):
    assert summary(lookup("Schloss", "de", "ru")) == "замок"
    assert summary(lookup("kosu", "sr", "en")) == "hair (of a person, on the head)"


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_wiktionary_translator_returns_trusted_html(kaikki):
    result = Translator("Wiktionary", "German", "Russian").translate(Term("Träumen"))

    assert isinstance(result, HtmlTranslation)
    assert result.translation == "сновидение, сон"
    assert result.html.startswith('<div class="wiktionary">')


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_wiktionary_translator_without_entries_found_nothing(kaikki):
    with pytest.raises(TranslatorError) as error:
        WiktionaryTranslator("english", "russian").translate(Term("nonexistent"))

    assert error.value.kind == TranslatorError.NOT_FOUND


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_wiktionary_translator_names_kaikki_when_it_is_unreachable(kaikki):
    kaikki.fail("kaikki.org", httpx.ConnectError("down"))

    with pytest.raises(TranslatorError) as error:
        WiktionaryTranslator("english", "russian").translate(Term("spring"))

    assert (error.value.kind, error.value.service) == (
        TranslatorError.NETWORK,
        "Wiktionary (kaikki.org)",
    )


@allure.epic("Translators")
@allure.feature("Wiktionary")
def test_wiktionary_translator_refuses_a_language_without_data():
    with pytest.raises(TranslatorError) as error:
        WiktionaryTranslator("french", "russian")

    assert error.value.kind == TranslatorError.UNSUPPORTED


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


def _popup(client, user, book, word_id="1"):
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
def test_popup_shows_the_sense_list_and_remembers_the_first_sense(kaikki, client, user, book):
    _page(book, "Early springs came.")

    data = _popup(client, user, book).json()

    assert data["html"] is True
    assert "error" not in data
    assert data["article"].startswith('<div class="wiktionary">')
    assert "CC BY-SA 4.0" in data["article"]
    assert TranslationHistory.objects.get(user=user).translation == "весна"


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.django_db
def test_popup_reads_the_words_place_in_its_sentence(kaikki, client, user, book):
    _page(book, "We flew to China last year.")

    data = _popup(client, user, book, word_id="3").json()

    assert data["article"].index("Китай") < data["article"].index("фарфор")
    assert TranslationHistory.objects.get(user=user).translation == "Китай"


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.django_db
def test_popup_for_a_missing_entry_is_an_alert(kaikki, client, user, book):
    _page(book, "Early nonexistent came.")

    data = _popup(client, user, book).json()

    assert data["error"] is True
    assert "Wiktionary found no translation." in data["article"]
    assert not TranslationHistory.objects.filter(user=user).exists()


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.django_db
def test_popup_when_kaikki_is_unreachable_is_the_network_alert(kaikki, client, user, book):
    _page(book, "Early springs came.")
    kaikki.fail("kaikki.org", httpx.ConnectTimeout("down"))

    data = _popup(client, user, book).json()

    assert data["error"] is True
    assert data["kind"] == TranslatorError.NETWORK
    assert "Wiktionary (kaikki.org) is not reachable." in data["article"]
    assert not TranslationHistory.objects.filter(user=user).exists()


@allure.epic("Translators")
@allure.feature("Wiktionary")
@pytest.mark.django_db
def test_sidebar_article_is_the_sense_list_unescaped(kaikki, client, user, book):
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
