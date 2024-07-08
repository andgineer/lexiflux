"""AI lexical articles."""

import json
import os
from functools import lru_cache
from typing import Any, Dict, List, Iterable, Union

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mistralai import ChatMistralAI
import openai
from langchain.schema import BaseOutputParser
from pydantic import Field
from django.core.cache import cache

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
    # https://docs.anthropic.com/en/docs/models-overview
    "claude-3-5-sonnet-20240620": {
        "title": "Claude 3.5 Sonnet",
        "model": ChatAnthropic,
        "suffix": "💡3.5",  # U+1F4A1
    },
    "gemini-pro": {
        "title": "Gemini Pro",
        "model": ChatGoogleGenerativeAI,
        "suffix": "🌀",
    },
    "mistral-medium": {
        "title": "Mistral Medium",
        "model": ChatMistralAI,
        "suffix": "🌪️",
    },
}


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
    """AI lexical articles.

    As `data` expect
    - book_code: str
    - page_number: int
    - word_ids: List[int]  # for all words in the `term`
    - text: str
    - term: str
    - text_language: str
    - user_language: str
    """

    ChatMessages = List[SystemMessage | HumanMessage | AIMessage]

    def __init__(self) -> None:
        openai.api_key = os.getenv("OPENAI_API_KEY")
        # alternatively set LANGCHAIN_API_KEY

        self._articles_templates = self._create_article_templates()
        self._model_cache: Dict[str, ChatOpenAI] = {}

    def article_names(self) -> list[str]:
        """Return a list of all available Lexical Article names."""
        return list(self._articles_templates.keys())

    def get_article(self, article_name: str, params: Dict[str, Any], data: Dict[str, Any]) -> str:
        """Generate the article based on data."""
        return self._get_article_cached(
            article_name, self._hashable_dict(params), self._hashable_dict(data)
        )

    def detect_sentence(
        self,
        article_name: str,
        hashable_params: tuple[tuple[str, Any]],
        hashable_data: tuple[tuple[str, Any]],
    ) -> Dict[str, str]:
        """Return already detected sentence for the first word in the `term`.

        If the sentence is not detected, it will be detected and returned.
        """
        data = dict(hashable_data)
        text_language = data["text_language"]
        user_language = data["user_language"]
        book_code = data["book_code"]
        page_number = data["page_number"]
        word_ids = data["word_ids"]
        cache_key = (
            f"sentences:{text_language}:{user_language}:{book_code}:{page_number}:{word_ids[0]}"
        )
        try:
            sentence = cache.get(cache_key)
            if sentence is None:
                sentence = self._detect_sentence(article_name, hashable_params, hashable_data)
                cache.set(cache_key, sentence, timeout=None)
        except Exception:  # pylint: disable=broad-except
            # Django is not inited
            sentence = self._detect_sentence(article_name, hashable_params, hashable_data)
        return sentence  # type: ignore

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
    ) -> ChatOpenAI:
        model_key = self._get_model_key(article_name, text_language, user_language, model_name)

        if model_key not in self._model_cache:
            self._model_cache[model_key] = ChatOpenAI(
                model=model_name,
                temperature=0.5,
                api_key=os.getenv("OPENAI_API_KEY"),  # type: ignore
            )

        return self._model_cache[model_key]

    def _create_article_templates(self) -> Dict[str, Any]:
        text_parser = TextOutputParser()
        sentence_parser = SentenceOutputParser(retry_count=1)
        explain_parser = ExplainOutputParser(retry_count=1)
        examples_parser = ExamplesOutputParser(retry_count=1)

        translation_system_template = """Given the following text in {text_language},
translate to {user_language} language the term marked with double starts before and after the term, like this:
This is the sentence containing **the term**. 
Give translation of the term in the exact sentence where the term is (and not all occurrences in the text).
Put into result only the term translation.
If the text is not in {text_language}, prefix the result with the text language name in parentheses, like (Latin).
"""

        translation_prompt_template = ChatPromptTemplate.from_messages(
            [("system", translation_system_template), ("user", "The text is: {text}")]
        )

        lexical_system_template = """Given the following text in {text_language},
write {text_language} - {user_language} lexical article for the term marked with
double starts before and after the term, like this:
This is the sentence containing **the term**. 
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

        examples_system_template = """Given the following text in {text_language},
provide up to seven examples in {text_language} language of sentences with the term marked with
double starts before and after the term, like this:
This is the sentence containing **the term**.

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

    @lru_cache(maxsize=1000)
    def _detect_sentence(
        self,
        article_name: str,
        hashable_params: tuple[tuple[str, Any]],
        hashable_data: tuple[tuple[str, Any]],
    ) -> Dict[str, str]:
        """Mark with <sentence> the sentence with highlighted word(s) and detect its language."""
        params = dict(hashable_params)
        data = dict(hashable_data)

        preprocessing_template = """Given a text in {text_language}, identify the full sentence
that contains the word(s) marked with double asterisks **like this**.
Mark the sentence containing the marked word(s) with double vertical bars before
and after the sentence, like this: ||This is the marked sentence containing **the word**.||

Definition of a sentence: grammatical unit that consists of one or more words,
usually containing a subject and a predicate, and expresses a complete thought.
It typically begins with a capital letter and ends with a terminal punctuation mark.
Can be simple, containing a single independent clause (e.g., "The cat sleeps."), or complex,
containing one or more dependent clauses in addition to an independent clause
(e.g., "Although it was raining, we went for a walk.").
In identifying the sentence, ensure to include any dependent or subordinate clauses
that are part of the main thought.

Additionally, detect the language of the marked sentence, which may differ from
the {text_language}.

Return the result in JSON format with the following fields:
"text": The full input text with the marked sentence and highlighted word(s).
"detected_language": The detected language of the marked sentence, accurately reflects the actual language of the sentence.
        """
        preprocessing_prompt_template = ChatPromptTemplate.from_messages(
            [("system", preprocessing_template), ("user", "{text}")]
        )
        model_name = params.get("model", "gpt-3.5-turbo")
        model = self._get_or_create_model(
            article_name, data["text_language"], data["user_language"], model_name
        )

        chain = preprocessing_prompt_template | model | TextOutputParser()
        result = chain.invoke(data)
        return json.loads(result)  # type: ignore

    def _hashable_dict(self, d: Dict[str, Any]) -> tuple[tuple[str, Any]]:
        return tuple(sorted(d.items()))  # type: ignore

    @lru_cache(maxsize=1000)
    def _get_article_cached(
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

        if article_name in {"Sentence", "Explain"}:
            preprocessed_data = self.detect_sentence(article_name, hashable_params, hashable_data)
            data["text"] = preprocessed_data["text"]
            data["detected_language"] = preprocessed_data["detected_language"]

        model_name = params.get("model", "gpt-3.5-turbo")
        model = self._get_or_create_model(
            article_name, data["text_language"], data["user_language"], model_name
        )

        chain = templates["template"] | model | templates["parser"]

        return chain.invoke(data)  # type: ignore
