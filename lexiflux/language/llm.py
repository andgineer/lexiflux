"""AI lexical articles."""

import json
import os
from functools import lru_cache
from typing import Any, Dict, List, Iterable, Union, Tuple

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_mistralai import ChatMistralAI
from langchain_community.llms import Ollama  # pylint: disable=no-name-in-module

import openai
from langchain.schema import BaseOutputParser
from pydantic import Field

from lexiflux.language.sentence_extractor_llm import (
    SENTENCE_START_MARK,
    SENTENCE_END_MARK,
    WORD_START_MARK,
    WORD_END_MARK,
)
from lexiflux.language.word_extractor import parse_words
from lexiflux.models import BookPage

ChatModels = {
    "gpt-3.5-turbo": {
        "title": "GPT-3.5 Turbo",
        "model": ChatOpenAI,
        "suffix": "⚙️3.5",
    },
    "gpt-4-turbo": {
        "title": "GPT-4 Turbo",
        "model": ChatOpenAI,
        "suffix": "⚙️4",
    },
    "gpt-4-turbo-preview": {
        "title": "GPT-4 Turbo Preview",
        "model": ChatOpenAI,
        "suffix": "⚙️4+",
    },
    "llama3": {
        "title": "LLAMA 3",
        "model": Ollama,
        "suffix": "🦙3",
    },
    "zephyr": {
        "title": "Zephyr 7B",
        "model": Ollama,
        "suffix": "🌬️7B",
    },
    # # https://docs.anthropic.com/en/docs/models-overview
    # "claude-3-5-sonnet-20240620": {
    #     "title": "Claude 3.5 Sonnet",
    #     "model": ChatAnthropic,
    #     "suffix": "💡3.5",  # U+1F4A1
    # },
    # "gemini-pro": {
    #     "title": "Gemini Pro",
    #     "model": ChatGoogleGenerativeAI,
    #     "suffix": "🌀",
    # },
    # "mistral-medium": {
    #     "title": "Mistral Medium",
    #     "model": ChatMistralAI,
    #     "suffix": "🌪️",
    # },
}


def find_nth_occurrence(substring: str, string: str, occurrence: int) -> int:
    """Find the nth occurrence (1 - first, etc) of a substring in a string."""
    start = -1
    for _ in range(occurrence):
        start = string.find(substring, start + 1)
        if start == -1:
            return -1
    return start


class TextOutputParser(BaseOutputParser[str]):
    """Simple output parser."""

    def parse(self, text: str) -> str:
        return text


class BaseJsonParser(BaseOutputParser[str]):
    """Base parser for JSON output."""

    retry_count: int = Field(default=1, description="Number of retry attempts for JSON parsing")

    def remove_delimiters(self, text: str, delimiters: Iterable[str] = ("||", "**")) -> str:
        """Remove delimiters from text."""
        for delimiter in delimiters:
            text = text.replace(delimiter, "")
        return text

    def parse_json(self, text: str) -> Union[Dict[str, Any], str]:
        """Parse JSON with retry logic.

        Return just text if the retries exhausted.
        """
        for _ in range(self.retry_count + 1):
            try:
                return json.loads(text)  # type: ignore
            except json.JSONDecodeError:
                pass  # ignore up to retry_count
        return text


class SentenceOutputParser(BaseJsonParser):
    """Sentence output parser."""

    def parse(self, text: str) -> str:
        json_result = self.parse_json(text)
        if isinstance(json_result, str) or "translation" not in json_result:
            return text  # return text if parsing failed
        detected_language = json_result.get("detected_language", "")
        expected_language = json_result.get("expected_language", "")
        comments = json_result.get("comments")
        if comments is not None:
            comments = self.remove_delimiters(comments)
            if "no comments" in comments.lower() or comments.lower().strip() == "none":
                comments = ""
        else:
            comments = ""
        if comments:
            comments = f"<hr>{comments}"
        translation = self.remove_delimiters(json_result["translation"])
        if detected_language.lower() != expected_language.lower():
            # todo: if the detected language is in same language group ignore it
            translation = f"({detected_language}) {translation}"
        return f"""{translation}<hr>{comments}"""


class ExplainOutputParser(BaseJsonParser):
    """Explain output parser."""

    def parse(self, text: str) -> str:
        json_result = self.parse_json(text)
        if isinstance(json_result, str) or "explanation" not in json_result:
            return text  # return text if parsing failed
        # detected_language = json_result.get("detected_language", "")
        # expected_language = json_result.get("expected_language", "")
        explanation = self.remove_delimiters(json_result["explanation"])
        translation = self.remove_delimiters(json_result["translation"])
        return f"""{explanation}<hr>{translation}"""


class ExamplesOutputParser(BaseJsonParser):
    """Examples output parser."""

    def parse(self, text: str) -> str:
        json_result = self.parse_json(text)
        if isinstance(json_result, str) or not isinstance(json_result, list):
            return text  # return text if parsing failed
        result = []
        for item in json_result:
            example = self.remove_delimiters(item["example"])
            translation = self.remove_delimiters(item["translation"])
            result.append(f"""<p>{example}</p><p>{translation}</>""")
        return "<hr>".join(result)


class Llm:  # pylint: disable=too-few-public-methods
    """AI lexical articles."""

    ChatMessages = List[SystemMessage | HumanMessage | AIMessage]
    _model_cache: Dict[str, Any]

    def __init__(self) -> None:
        openai.api_key = os.getenv("OPENAI_API_KEY")
        # os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY")
        # os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
        # os.environ["MISTRAL_API_KEY"] = os.getenv("MISTRAL_API_KEY")
        self._articles_templates = self._create_article_templates()
        self._model_cache: Dict[str, Any] = {}

    def article_names(self) -> List[str]:
        """Return a list of all available Lexical Article names."""
        return list(self._articles_templates.keys())

    def generate_article(
        self, article_name: str, params: Dict[str, Any], data: Dict[str, Any]
    ) -> str:
        """Generate the article based on the data.

        Expects in `params`:
        - model: LLM model name from ChatModels.keys()
        Expects in `data`:
        - text:
            highlighted words marked with WORD_START_MARK and WORD_END_MARK
            sentences that contained the highlighted words marked with SENTENCE_START_MARK
            and SENTENCE_END_MARK
        - word_slices:
            list of tuples with start and end indices of words in the text
            to get the last word in text: start, end = word_slices[-1]; text[start:end]
        - term_word_ids: list of the highlighted word IDs, expected to be contiguous
        - text_language: Expected text language (could be wrong if this is phrase
            in different language)
        - user_language: User's language

        Returns:
            HTML formatted article.
        """
        return self._generate_article_cached(
            article_name, self._hashable_dict(params), self._hashable_dict(data)
        )

    def prepare_data(
        self,
        text: str,
        term: str,
        term_occurence: int = 1,
    ) -> Dict[str, Any]:
        """From the text given prepare the data to generate an LLM article.

        Convenient way to debug the LLM.
        If term is included in the text multiple times, you can specify which occurrence to use
        (1 - 1st, etc).

        Return: dict with "term_word_ids" and "word_slices" ready to use in generate_article().
        """
        word_slices, _ = parse_words(text)
        term_start = find_nth_occurrence(term, text, term_occurence)
        term_end = term_start + len(term)
        # find the word slices that contain the term
        term_word_ids = []
        for i, (start, end) in enumerate(word_slices):
            if start >= term_start and end <= term_end:
                term_word_ids.append(i)

        data = {
            "word_slices": word_slices,
            "term_word_ids": term_word_ids,
        }
        return data

    def mark_term_and_sentence(  # pylint: disable=too-many-locals
        self,
        hashable_data: tuple[tuple[str, Any]],
    ) -> Dict[str, str]:
        """Mark in the text the term and sentence(s) that contains it.

        Expects in `data`:
        - text:
        - word_slices:
            list of tuples with start and end indices of words in the text
        - term_word_ids:
            list of the highlighted word IDs, expected to be contiguous
        - text_language:
            Expected text language (could be wrong if this is phrase in different language)

        Returns:
            {
                "text":
                    detected sentence(s) marked with SENTENCE_START_MARK and SENTENCE_END_MARK
                    and term marked with WORD_START_MARK and WORD_END_MARK
                "detected_language":
                    detected language of the sentence(s)
            }
        """
        data = dict(hashable_data)
        text = data["text"]
        word_slices: List[Tuple[int, int]] = data["word_slices"]
        term_word_ids: List[int] = data["term_word_ids"]
        page: BookPage = data["page"]
        context_start_word = data["context_start_word"]

        mapping = page.word_sentence_mapping
        page_term_word_ids = [wid + context_start_word for wid in term_word_ids]
        term_sentences = set(mapping[word_id] for word_id in page_term_word_ids)
        term_sentences_word_ids = [
            word_id - context_start_word
            for word_id, sentence_id in mapping.items()
            if sentence_id in term_sentences
            and word_id - context_start_word >= 0
            and word_id - context_start_word < len(word_slices)
        ]

        min_word_id = min(term_sentences_word_ids)
        max_word_id = max(term_sentences_word_ids)

        try:
            sentence_start = word_slices[min_word_id][0]
            sentence_end = word_slices[max_word_id][1]

            marked_text = (
                f"{text[:sentence_start]}{SENTENCE_START_MARK}"
                f"{text[sentence_start:sentence_end]}{SENTENCE_END_MARK}{text[sentence_end:]}"
            )
        except IndexError as e:
            print(f"Error detecting sentence, mark full text instead: {e}")
            marked_text = f"{SENTENCE_START_MARK}{text}{SENTENCE_END_MARK}"

        term_start = word_slices[term_word_ids[0]][0] + len(SENTENCE_START_MARK)
        term_end = word_slices[term_word_ids[-1]][1] + len(SENTENCE_START_MARK)
        marked_text = (
            f"{marked_text[:term_start]}{WORD_START_MARK}"
            f"{marked_text[term_start:term_end]}{WORD_END_MARK}"
            f"{marked_text[term_end:]}"
        )
        print(f"Marked text: {marked_text}")
        return {
            "text": marked_text,
            "detected_language": data["text_language"],
        }

    def _get_model_key(
        self,
        article_name: str,  # pylint: disable=unused-argument
        text_language: str,  # pylint: disable=unused-argument
        user_language: str,  # pylint: disable=unused-argument
        model_name: str,
    ) -> str:
        return f"{model_name}"  # {article_name}_{text_language}_{user_language}_

    def _get_or_create_model(
        self, article_name: str, text_language: str, user_language: str, model_name: str
    ) -> Any:
        model_key = self._get_model_key(article_name, text_language, user_language, model_name)

        if model_key not in self._model_cache:
            model_info = ChatModels.get(model_name)
            if not model_info:
                raise ValueError(f"Unsupported model: {model_name}")

            model_class = model_info["model"]

            if model_class == ChatOpenAI:
                self._model_cache[model_key] = model_class(
                    model=model_name,
                    temperature=0.5,
                )
            if model_class == Ollama:
                self._model_cache[model_key] = model_class(
                    model=model_name,
                    temperature=0.5,
                )
            # elif model_class == ChatAnthropic:
            #     self._model_cache[model_key] = model_class(
            #         model=model_name,
            #         temperature=0.5,
            #     )
            # elif model_class == ChatGoogleGenerativeAI:
            #     self._model_cache[model_key] = model_class(
            #         model=model_name,
            #         temperature=0.5,
            #     )
            elif model_class == ChatMistralAI:
                self._model_cache[model_key] = model_class(
                    model=model_name,
                    temperature=0.5,
                )
            else:
                raise ValueError(f"Unsupported model class: {model_class}")

        return self._model_cache[model_key]

    def _create_article_templates(self) -> Dict[str, Any]:
        text_parser = TextOutputParser()
        sentence_parser = SentenceOutputParser(retry_count=1)
        explain_parser = ExplainOutputParser(retry_count=1)
        examples_parser = ExamplesOutputParser(retry_count=1)

        translation_system_template = """Below given a text with the sentence
in {detected_language} language
marked with double vertical bars before and after the sentence, like this:
||This is the marked sentence containing **the word**.||
Inside the sentence, the term is marked with double stars - like
**the word** in the example above.
Translate to {user_language} language the term.
Give translation of the term in the exact sentence where the term is (and not all occurrences in the text).
Put into result only the term translation.
If the text is not in {text_language}, prefix the result with the text language name in parentheses, like (Latin).
"""

        translation_prompt_template = ChatPromptTemplate.from_messages(
            [("system", translation_system_template), ("user", "The text is: {text}")]
        )

        lexical_system_template = """Below given a text with the sentence
in {detected_language} language
marked with double vertical bars before and after the sentence, like this:
||This is the marked sentence containing **the word**.||
Inside the sentence, the term is marked with double stars - like
**the word** in the example above.
Write {text_language} - {user_language} lexical article for the term. 
The article should be in {user_language}.
The article includes different meanings, grammar attributes of them - part of the speech,
genre, number, countability and other.
Article should be in compact nice style like in good dictionaries.
Include declination table and other information you expect to see in a good dictionary
like Oxford Dictionary.
If you are sure the text is in a different language, write the article based on that language and indicate
it by starting the result with the detected language name in parentheses.
Give the result in HTML formatting, without any block marks."""

        lexical_prompt_template = ChatPromptTemplate.from_messages(
            [("system", lexical_system_template), ("user", "The text is: {text}")]
        )

        examples_system_template = """Below given a text with the sentence
in {detected_language} language
marked with double vertical bars before and after the sentence, like this:
||This is the marked sentence containing **the word**.||
Inside the sentence, the term is marked with double stars - like
**the word** in the example above.
Provide up to seven examples in {text_language} language of sentences with the term.

Return in JSON format without any additional block marks or labels.
The JSON should contain array of objects with the following fields:
"example": the example sentence.
"translation": translation of the sentence to {user_language} language.

Critical instructions:
- Recheck language in the fields "translation".
If is not {user_language}, translate the field to {user_language} language.
"""

        examples_prompt_template = ChatPromptTemplate.from_messages(
            [("system", examples_system_template), ("user", "The text is: {text}")]
        )

        explain_system_template = """Below given a text with the sentence
in {detected_language} language
marked with double vertical bars before and after the sentence, like this:
||This is the marked sentence containing **the word**.||
Inside the sentence, the term is marked with double stars - like
**the word** in the example above.

Return in JSON format without any additional block marks or labels the following fields:
- "explanation": in {text_language} language explain the usage of the marked term
in the marked sentence, and not in other occurrences of the text.
You may use surrounding text for better explanation, but explain the marked usage only.
- "translation": translation of the explanation to {user_language}.
- "expected_language": The name of {text_language} language in {user_language}.
- "detected_language": The name of {detected_language} language in {user_language}.

Critical instructions:
- Recheck language in the field "translation".
If is not {user_language}, translate the field to {user_language} language.
"""

        explain_prompt_template = ChatPromptTemplate.from_messages(
            [("system", explain_system_template), ("user", "The text is: {text}")]
        )

        sentence_system_template = """Below given a text with the sentence
marked with double vertical bars before and after the sentence, like this:
||This is the marked sentence containing **the word**.||
Return in JSON format without any additional block marks or labels the following fields:
- "translation": translate the marked sentence only from {detected_language}
to {user_language} language.
You may use surrounding text for better translation, but translate the marked sentence only.
- "comments": explain difficulties (if any) in the marked {detected_language} sentence
for a {user_language} speaker.
The explanation should be in {user_language} language
If there are no comments, set this field to null.
Do not include phrases like "There are no difficult words" or "No comments".
- "expected_language": The name of {text_language} language in {user_language}.
- "detected_language": The name of {detected_language} language in {user_language}.

Critical instructions:
- Do not add a language name (e.g., "(Serbian)") to translation or comments.
- Recheck language in fields "translation" and "comments".
If is not {user_language}, translate the fields to {user_language} language.
"""
        # todo: still sometimes return translation / comment not in user language
        # add step to translate them

        sentence_prompt_template = ChatPromptTemplate.from_messages(
            [("system", sentence_system_template), ("user", "The text is: {text}")]
        )

        return {
            "Translate": {"template": translation_prompt_template, "parser": text_parser},
            "Lexical": {"template": lexical_prompt_template, "parser": text_parser},
            "Examples": {"template": examples_prompt_template, "parser": examples_parser},
            "Explain": {"template": explain_prompt_template, "parser": explain_parser},
            "Sentence": {"template": sentence_prompt_template, "parser": sentence_parser},
        }

    def _hashable_dict(self, d: Dict[str, Any]) -> Tuple[Tuple[str, Any], ...]:
        return tuple((k, tuple(v) if isinstance(v, list) else v) for k, v in sorted(d.items()))

    @lru_cache(maxsize=1000)
    def _generate_article_cached(
        self,
        article_name: str,
        hashable_params: tuple[tuple[str, Any]],
        hashable_data: tuple[tuple[str, Any]],
    ) -> str:
        """Cached get article."""
        params = dict(hashable_params)
        data = dict(hashable_data)
        templates = self._articles_templates[article_name]

        if article_name not in self._articles_templates:
            raise ValueError(f"Lexical article '{article_name}' not found.")

        marked_text = self.mark_term_and_sentence(hashable_data)
        data["text"] = marked_text["text"]
        data["detected_language"] = marked_text["detected_language"]

        model_name = params.get("model", "gpt-3.5-turbo")
        model = self._get_or_create_model(
            article_name, data["text_language"], data["user_language"], model_name
        )

        chain = templates["template"] | model | templates["parser"]

        return chain.invoke(data)  # type: ignore
