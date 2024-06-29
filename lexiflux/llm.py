"""AI lexical articles."""

import json
import os
from functools import lru_cache
from typing import Any, Dict, List, Iterable

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
import openai
from langchain.schema import BaseOutputParser
from pydantic import Field


class SimpleOutputParser(BaseOutputParser[str]):
    """Simple output parser."""

    def parse(self, text: str) -> str:
        return text


class SentenceOutputParser(BaseOutputParser[str]):
    """Sentence output parser."""

    retry_count: int = Field(default=1, description="Number of retry attempts for JSON parsing")

    def remove_delimiters(self, text: str, delimiters: Iterable[str] = ("||", "**")) -> str:
        """Remove delimiters from text."""
        for delimiter in delimiters:
            text = text.replace(delimiter, "")
        return text

    def parse(self, text: str) -> str:
        for _ in range(self.retry_count + 1):
            try:
                json_result = json.loads(text)
                if "translation" not in json_result:
                    json_result["translation"] = text
            except json.JSONDecodeError:
                if _ == self.retry_count:
                    json_result = {"translation": text}
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


class Llm:  # pylint: disable=too-few-public-methods
    """AI lexical articles."""

    ChatMessages = List[SystemMessage | HumanMessage | AIMessage]

    def __init__(self) -> None:
        openai.api_key = os.getenv("OPENAI_API_KEY")
        # alternatively set LANGCHAIN_API_KEY

        self._articles_templates = self._create_article_templates()
        self._model_cache: Dict[str, ChatOpenAI] = {}

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
        parser = SimpleOutputParser()
        sentence_parser = SentenceOutputParser(retry_count=1)

        translation_system_template = """Given the following text in {text_language},
translate the term marked with <span class="highlighted-term"> tag to {user_language}. 
Give translation of the term in the exact sentence where the term is (and not all occurrences in the text).
Put into result only the term translation.
If the text is not in {text_language}, prefix the result with the text language name in parentheses, like (Latin).
"""

        translation_prompt_template = ChatPromptTemplate.from_messages(
            [("system", translation_system_template), ("user", "{text}")]
        )

        dictionary_system_template = """Given the term in {text_language},
write {text_language} - {user_language} dictionary article for the term.
The article should be in {user_language}.
Include grammar attributes - part of the speech, genre, number, countability and other grammar attributes.
All grammar attributes should be on one line in a compact way with abbreviations like in good dictionaries.
Include different meanings, declination table and other information you expect to see in a good dictionary
like Oxford, but do not include examples.
If you are sure the text is in a different language, write the article based on that language and indicate
it by starting the result with the detected language name in parentheses.
Give the result in HTML formatting, without any block marks."""

        dictionary_prompt_template = ChatPromptTemplate.from_messages(
            [("system", dictionary_system_template), ("user", "The term is: {term}")]
        )

        examples_system_template = """Given the term in {text_language},
provide up to seven examples in {text_language} of sentences with the term.
After each example, provide the translation of the example to {user_language} in a separate paragraph 
using the <p> tag.
Do not prefix the translation with ({user_language}) or with "Translation." 
Separate examples with <hr> tags. 
Provide the result in HTML formatting, without any block marks.

Ensure your response adheres strictly to these instructions:
- Do not repeat examples.
- If you detect a language different from {text_language}, mention that, 
but do not mention the language if it is {text_language}.
- Do not mark the translation with "Translation" or similar terms.
"""

        examples_prompt_template = ChatPromptTemplate.from_messages(
            [("system", examples_system_template), ("user", "The term is: {term}")]
        )

        explain_system_template = """Explain using only {text_language}, the usage
of the term marked in the text with a <span class="highlighted-term"> tag.
Explain the usage only in the sentence where the term
is marked with the <span class="highlighted-term"> tag, and not in other occurrences of the text.
Only if the text is not in {text_language}, start with the detected language in parentheses.
After <hr> provide the translation of the explanation to {user_language}.
Give the result in HTML formatting without any additional block marks or labels.

Ensure your response adheres strictly to these instructions:
- Use {text_language} for the initial explanation.
- Never put into the result names of the languages {text_language} or {user_language}.
- Explain the exact sentence where the term is marked with the <span class="highlighted-term"> tag.
Do not mention usage of the term in sentences where it is not marked
with the <span class="highlighted-term"> tag.
"""

        explain_prompt_template = ChatPromptTemplate.from_messages(
            [("system", explain_system_template), ("user", "{text}")]
        )

        sentence_system_template = """Below given a text with the sentence
marked with double vertical bars before and after the sentence, like this:
||This is the marked sentence containing **the word**.||
Return in JSON format without any additional block marks or labels the following fields:
- "translation": translation from {detected_language} to {user_language} for the marked sentence.
Use surrounding context for better translation, but translate the marked sentence only,
not the text around.
- "comments": explanation of difficulties in the marked {detected_language} sentence
for a {user_language} speaker.
The explanation should be in {user_language} language
Use surrounding context for better comments if necessary.
If there are no comments, set this field to null.
Do not include phrases like "There are no difficult words" or "No comments".
- "expected_language": The name of {text_language} language written in {user_language}.
- "detected_language": The name of {detected_language} language written in {user_language}.

Critical instructions:
- Do not add a language name (e.g., "(Serbian)") to translation or comments.
- Before returning result detect language in the fields "translation" and "comments".
If is not {user_language}, translate the fields to {user_language} language.
"""
        # todo: still sometimes return translation / comment not in user language
        # add step to translate them

        sentence_prompt_template = ChatPromptTemplate.from_messages(
            [("system", sentence_system_template), ("user", "The text is: {text}")]
        )

        return {
            "Translate": {"template": translation_prompt_template, "parser": parser},
            "Dictionary": {"template": dictionary_prompt_template, "parser": parser},
            "Examples": {"template": examples_prompt_template, "parser": parser},
            "Explain": {"template": explain_prompt_template, "parser": parser},
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

        chain = preprocessing_prompt_template | model | SimpleOutputParser()
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

        preprocessed_data = self._detect_sentence(article_name, hashable_params, hashable_data)
        data["text"] = preprocessed_data["text"]
        data["detected_language"] = preprocessed_data["detected_language"]

        model_name = params.get("model", "gpt-3.5-turbo")
        model = self._get_or_create_model(
            article_name, data["text_language"], data["user_language"], model_name
        )

        chain = templates["template"] | model | templates["parser"]

        return chain.invoke(data)  # type: ignore

    def get_article(self, article_name: str, params: Dict[str, Any], data: Dict[str, Any]) -> str:
        """Create the article based on data."""
        return self._get_article_cached(
            article_name, self._hashable_dict(params), self._hashable_dict(data)
        )

    def article_names(self) -> list[str]:
        """Return a list of all available Lexical Article names."""
        return list(self._articles_templates.keys())
