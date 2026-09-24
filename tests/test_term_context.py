import re
from contextlib import contextmanager
from unittest.mock import PropertyMock, patch

import allure
import pytest

from lexiflux.language.term_context import term_context
from lexiflux.models import BookPage, TranslationHistory
from lexiflux.views.lexical_views import get_context_for_translation_history

SENTENCES = [
    "Alpha beta gamma.",
    "Delta epsilon zeta eta theta iota kappa.",
    "Lambda mu.",
    "Nu xi omicron pi rho sigma tau upsilon.",
    "Phi chi psi omega.",
    "One two three four five six seven.",
]


def build_page(sentences, separator=" "):
    content = separator.join(sentences)
    words, mapping = [], {}
    pos = 0
    for sentence_id, sentence in enumerate(sentences):
        start = content.index(sentence, pos)
        for token in re.finditer(r"<[^>]+>|\w+", sentence):
            if token.group().startswith("<"):
                continue
            mapping[len(words)] = sentence_id
            words.append((start + token.start(), start + token.end()))
        pos = start + len(sentence)
    return content, words, mapping


@contextmanager
def fake_page(book, sentences, separator=" "):
    content, words, mapping = build_page(sentences, separator)
    page = BookPage.objects.get(book=book, number=1)
    with (
        patch("lexiflux.models.BookPage.words", new_callable=PropertyMock, return_value=words),
        patch(
            "lexiflux.models.BookPage.word_sentence_mapping",
            new_callable=PropertyMock,
            return_value=mapping,
        ),
        patch("lexiflux.models.BookPage.content", new_callable=PropertyMock, return_value=content),
    ):
        yield page


@pytest.fixture
def page(book):
    with fake_page(book, SENTENCES) as page:
        yield page


@allure.epic("AI articles")
@allure.feature("Term context")
@pytest.mark.parametrize(
    "word_ids, word, sentence",
    [
        ([3], "Delta", "Delta epsilon zeta eta theta iota kappa."),
        ([5, 6], "zeta eta", "Delta epsilon zeta eta theta iota kappa."),
        ([9, 10], "kappa. Lambda", "Delta epsilon zeta eta theta iota kappa. Lambda mu."),
        ([16], "rho", "Nu xi omicron pi rho sigma tau upsilon."),
        ([30], "seven", "One two three four five six seven."),
    ],
    ids=["single word", "multi-word", "across sentences", "middle", "last word of page"],
)
def test_term_context(page, word_ids, word, sentence):
    context = term_context(page, word_ids)
    assert context.word == word
    assert context.sentence == sentence


@allure.epic("AI articles")
@allure.feature("Term context")
@pytest.mark.parametrize(
    "word_ids, sentence",
    [
        (
            [10],
            "Delta epsilon zeta eta theta iota kappa. Lambda mu. "
            "Nu xi omicron pi rho sigma tau upsilon.",
        ),
        (
            [20],
            "Nu xi omicron pi rho sigma tau upsilon. Phi chi psi omega. "
            "One two three four five six seven.",
        ),
        ([0], "Alpha beta gamma. Delta epsilon zeta eta theta iota kappa."),
    ],
    ids=["two words", "four words", "first sentence of page"],
)
def test_short_sentence_extended_with_neighbours(page, word_ids, sentence):
    assert term_context(page, word_ids).sentence == sentence


@allure.epic("AI articles")
@allure.feature("Term context")
def test_short_last_sentence_extended_with_previous_only(book):
    with fake_page(book, ["One two three four five six seven.", "The end."]) as page:
        context = term_context(page, [8])
    assert context.word == "end"
    assert context.sentence == "One two three four five six seven. The end."


@allure.epic("AI articles")
@allure.feature("Term context")
def test_single_short_sentence_page(book):
    with fake_page(book, ["Hi there."]) as page:
        assert term_context(page, [1]).sentence == "Hi there."


@allure.epic("AI articles")
@allure.feature("Term context")
def test_html_is_stripped_and_blocks_keep_words_apart(book):
    sentences = ["<p>Hello <b>big</b> world.</p>", "<p>Next one &amp; more.</p>"]
    with fake_page(book, sentences, separator="") as page:
        context = term_context(page, [1])
    assert context.word == "big"
    assert context.sentence == "Hello big world. Next one & more."


@allure.epic("AI articles")
@allure.feature("Term context")
def test_offsets(page):
    content = page.content
    context = term_context(page, [9, 10])
    assert content[slice(*context.term_span)] == "kappa. Lambda"
    assert content[slice(*context.sentence_span)] == (
        "Delta epsilon zeta eta theta iota kappa. Lambda mu"
    )


@allure.epic("AI articles")
@allure.feature("Translation history context")
@pytest.mark.parametrize(
    "word_ids, expected",
    [
        ([0], "{M}{M} beta gamma{M}. Delta epsilon zeta eta theta iota kappa. Lambda mu"),
        (
            [2],
            "{M}Alpha beta {M}{M}. Delta epsilon zeta eta theta iota kappa. Lambda mu. "
            "Nu xi omicron pi rho sigma tau upsilon",
        ),
        (
            [3],
            "Alpha beta gamma. {M}{M} epsilon zeta eta theta iota kappa{M}. Lambda mu. "
            "Nu xi omicron pi rho sigma tau upsilon",
        ),
        (
            [5, 6],
            "Alpha beta gamma. {M}Delta epsilon {M} theta iota kappa{M}. Lambda mu. "
            "Nu xi omicron pi rho sigma tau upsilon",
        ),
        (
            [9],
            "Alpha beta gamma. {M}Delta epsilon zeta eta theta iota {M}{M}. Lambda mu. "
            "Nu xi omicron pi rho sigma tau upsilon",
        ),
        (
            [10],
            "Alpha beta gamma. Delta epsilon zeta eta theta iota kappa. {M}{M} mu{M}. "
            "Nu xi omicron pi rho sigma tau upsilon. Phi chi psi omega",
        ),
        (
            [9, 10, 11],
            "Alpha beta gamma. {M}Delta epsilon zeta eta theta iota {M}{M}. "
            "Nu xi omicron pi rho sigma tau upsilon. Phi chi psi omega",
        ),
        (
            [16],
            "Delta epsilon zeta eta theta iota kappa. Lambda mu. "
            "{M}Nu xi omicron pi {M} sigma tau upsilon{M}. Phi chi psi omega. "
            "One two three four five six seven",
        ),
        (
            [20],
            "Lambda mu. Nu xi omicron pi rho sigma tau upsilon. {M}{M} chi psi omega{M}. "
            "One two three four five six seven",
        ),
        (
            [21],
            "Lambda mu. Nu xi omicron pi rho sigma tau upsilon. {M}Phi {M} psi omega{M}. "
            "One two three four five six seven",
        ),
        (
            [23],
            "Nu xi omicron pi rho sigma tau upsilon. {M}Phi chi psi {M}{M}. "
            "One two three four five six seven",
        ),
        (
            [27, 28],
            "Nu xi omicron pi rho sigma tau upsilon. Phi chi psi omega. "
            "{M}One two three {M} six seven{M}",
        ),
        ([30], "Phi chi psi omega. {M}One two three four five six {M}{M}"),
        (
            [8, 12],
            "Alpha beta gamma. {M}Delta epsilon zeta eta theta {M} "
            "xi omicron pi rho sigma tau upsilon{M}. Phi chi psi omega",
        ),
    ],
)
def test_translation_history_context_format_unchanged(page, word_ids, expected):
    assert get_context_for_translation_history(page, word_ids) == expected.replace(
        "{M}", TranslationHistory.CONTEXT_MARK
    )
