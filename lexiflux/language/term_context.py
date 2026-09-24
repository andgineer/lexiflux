import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from lexiflux.language.parse_html_text_content import extract_content_from_html

if TYPE_CHECKING:
    from lexiflux.models import BookPage

MIN_SENTENCE_WORDS = 6

_BLOCK_TAG = re.compile(
    r"(</?(?:p|div|br|h[1-6]|li|ul|ol|tr|td|th|table|blockquote|section|article|pre|hr)\b[^>]*>)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TermContext:
    word: str
    sentence: str
    # Character offsets in the page content. `sentence_span` is the term's own
    # sentence(s), before any short-sentence extension.
    term_span: tuple[int, int]
    sentence_span: tuple[int, int]


def sentences_word_ids(page: "BookPage", first_sentence: int, last_sentence: int) -> list[int]:
    words_count = len(page.words)
    return sorted(
        word_id
        for word_id, sentence_id in page.word_sentence_mapping.items()
        if first_sentence <= sentence_id <= last_sentence and 0 <= word_id < words_count
    )


def words_span(page: "BookPage", word_ids: list[int]) -> tuple[int, int]:
    return page.words[min(word_ids)][0], page.words[max(word_ids)][1]


def plain_text(html: str) -> str:
    # Block tags between sentences would otherwise glue the last word of one to the next.
    return " ".join(extract_content_from_html(_BLOCK_TAG.sub(r" \1", html)).split())


def _extended_sentences(page: "BookPage", first: int, last: int) -> tuple[int, int]:
    sentence_ids = sorted(set(page.word_sentence_mapping.values()))
    previous = [sid for sid in sentence_ids if sid < first]
    following = [sid for sid in sentence_ids if sid > last]
    return (previous[-1] if previous else first), (following[0] if following else last)


def _text_through_punctuation(page: "BookPage", word_ids: list[int]) -> str:
    # Runs to the next word so the closing punctuation and quotes stay with the sentence.
    start = page.words[word_ids[0]][0]
    next_word = word_ids[-1] + 1
    end = page.words[next_word][0] if next_word < len(page.words) else len(page.content)
    return plain_text(page.content[start:end])


def term_context(page: "BookPage", term_word_ids: list[int]) -> TermContext:
    mapping = page.word_sentence_mapping
    first_sentence = mapping[term_word_ids[0]]
    last_sentence = mapping[term_word_ids[-1]]

    sentence_ids = sentences_word_ids(page, first_sentence, last_sentence)
    if len(sentence_ids) < MIN_SENTENCE_WORDS:
        sentence_ids = sentences_word_ids(
            page,
            *_extended_sentences(page, first_sentence, last_sentence),
        )

    term_span = page.words[term_word_ids[0]][0], page.words[term_word_ids[-1]][1]
    return TermContext(
        word=extract_content_from_html(page.content[term_span[0] : term_span[1]]),
        sentence=_text_through_punctuation(page, sentence_ids),
        term_span=term_span,
        sentence_span=words_span(page, sentences_word_ids(page, first_sentence, last_sentence)),
    )
