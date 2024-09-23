"""Advanced sentence extraction utilities for the LexiFlux language module.

(!) Main risk here - we expect LLM to keep the input text exactly the same
except for the marked sentence.
"""

from typing import List, Tuple, Dict
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.schema import BaseOutputParser


class TextOutputParser(BaseOutputParser[str]):
    """Simple output parser."""

    def parse(self, text: str) -> str:
        return text


SENTENCE_START_MARK = "[FRAGMENT]"
SENTENCE_END_MARK = "[/FRAGMENT]"
WORD_START_MARK = "[HIGHLIGHT]"
WORD_END_MARK = "[/HIGHLIGHT]"


def break_into_sentences_llm(  # pylint: disable=too-many-locals
    plain_text: str,
    word_slices: List[Tuple[int, int]],
    term_word_ids: List[int],  # pylint: disable=redefined-outer-name
    lang_code: str = "en",
) -> Tuple[List[str], Dict[int, int]]:
    """
    Break plain text into sentences, mark the highlighted word, and map word IDs
    to sentence indices.

    Args:
    plain_text: The input text without HTML tags.
    word_slices: List of word start and end indices.
    term_word_ids: The ID of the word to be highlighted.
    lang_code: Language code of the text.

    Returns:
    Tuple[List[str], Dict[int, int]]: A tuple containing:
        - List of sentences
        - Dictionary mapping word index to sentence index
    """
    # Step 1: Mark the highlighted term with **
    term_start = word_slices[term_word_ids[0]][0]
    term_end = word_slices[term_word_ids[-1]][1]
    marked_text = (
        plain_text[:term_start]
        + WORD_START_MARK
        + plain_text[term_start:term_end]
        + WORD_END_MARK
        + plain_text[term_end:]
    )

    # Step 2: Use LLM to detect and mark the sentence
    marked_text_with_sentence = detect_sentence_llm(marked_text, lang_code)

    # Step 3: Extract sentences and create word_to_sentence mapping
    sentences_list = []
    map_word_to_sentence = {}
    current_sentence = 0

    sentence_start = marked_text_with_sentence.find(SENTENCE_START_MARK)
    if sentence_start == -1:
        return [], {}
    sentence_end = marked_text_with_sentence.find(
        SENTENCE_END_MARK, sentence_start + len(SENTENCE_START_MARK)
    )
    if sentence_end == -1:
        return [], {}

    # Extract the sentence and remove WORD_START_MARK and WORD_END_MARK
    marked_sentence = marked_text_with_sentence[
        sentence_start + len(SENTENCE_START_MARK) : sentence_end
    ]
    clean_sentence = marked_sentence.replace(WORD_START_MARK, "").replace(WORD_END_MARK, "")
    sentences_list.append(clean_sentence)
    # sentence end index after removing word and sentence marks
    sentence_end -= len(SENTENCE_START_MARK) + len(WORD_START_MARK) + len(WORD_END_MARK)

    for word_id, (word_start, word_end) in enumerate(word_slices):  # pylint: disable=redefined-outer-name
        if sentence_start <= word_start < sentence_end:
            # print(f"Word ID {word_id} (started at {word_start}) is in sentence:
            # {plain_text[0:word_start]}@@@{plain_text[word_start:word_end]}
            # @@@{plain_text[word_end:]}")
            map_word_to_sentence[word_id] = current_sentence
            word_slices[word_id] = (word_start, word_end)

    return sentences_list, map_word_to_sentence


def detect_sentence_llm(text: str, text_language: str) -> str:
    """Use LLM to detect and mark the sentence containing the highlighted word."""
    preprocessing_template = (
        "Given a text in {text_language}, identify the full sentence"
        "that contains the word(s) marked with double asterisks **like this**."
        "Mark the sentence containing the marked word(s) with double vertical bars before"
        "and after the sentence, like this:"
        f"{SENTENCE_START_MARK}This is the marked sentence "
        f"containing {WORD_START_MARK}the word{WORD_END_MARK}.{SENTENCE_END_MARK}"
        "Definition of a sentence: grammatical unit that consists of one or more words,"
        "usually containing a subject and a predicate, and expresses a complete thought."
        "It typically begins with a capital letter and ends with a terminal punctuation mark."
        "Can be simple, containing a single independent clause "
        "(e.g., 'The cat sleeps.'), or complex,"
        "containing one or more dependent clauses in addition to an independent clause"
        "(e.g., 'Although it was raining, we went for a walk.')."
        "In identifying the sentence, ensure to include any dependent or subordinate clauses"
        "that are part of the main thought."
        "Return the result as plain text with the marked sentence."
    )

    preprocessing_prompt_template = ChatPromptTemplate.from_messages(
        [("system", preprocessing_template), ("user", "{text}")]
    )

    model = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0.5,
    )

    chain = preprocessing_prompt_template | model | TextOutputParser()
    result = chain.invoke({"text": text, "text_language": text_language})

    return result


if __name__ == "__main__":
    # Example usage
    SAMPLE_TEXT = "The quick brown fox jumps over the lazy dog. It was a sunny day in the forest."
    sample_word_ids = [
        (0, 3),
        (4, 9),
        (10, 15),
        (16, 19),
        (20, 25),
        (26, 30),
        (31, 34),
        (35, 39),
        (40, 43),
        (44, 46),
        (47, 50),
        (51, 52),
        (53, 55),
        (56, 59),
        (60, 61),
        (62, 67),
        (68, 71),
        (72, 74),
        (75, 79),
        (80, 87),
        (87, 88),
    ]
    term_word_ids = [3]  # "jumps"

    sentences, word_to_sentence = break_into_sentences_llm(
        SAMPLE_TEXT, sample_word_ids, term_word_ids
    )

    print("Sentences:")
    for i, sentence in enumerate(sentences):
        print(f"{i}: {sentence}")

    print("\nWord to Sentence mapping:")
    for word_id, sentence_id in word_to_sentence.items():
        print(f"Word ID {word_id}: Sentence {sentence_id}")
