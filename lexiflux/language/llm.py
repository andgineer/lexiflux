"""AI lexical articles."""

import logging
import os
from functools import lru_cache
from typing import Any

import openai
import yaml
from django.conf import settings
from langchain.schema import BaseOutputParser
from langchain_anthropic import ChatAnthropic
from langchain_community.llms import Ollama  # pylint: disable=no-name-in-module
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mistralai import ChatMistralAI
from langchain_openai import ChatOpenAI

from lexiflux.language.parse_html_text_content import extract_content_from_html
from lexiflux.language.sentence_extractor_llm import (
    SENTENCE_END_MARK,
    SENTENCE_START_MARK,
    WORD_END_MARK,
    WORD_START_MARK,
)
from lexiflux.language.word_extractor import parse_words
from lexiflux.models import AIModelConfig, Book, BookPage, CustomUser

logger = logging.getLogger(__name__)

# Mapping of AI model names to their corresponding API KEY environment variable names
AI_MODEL_API_KEY_ENV_VAR = {
    "ChatOpenAI": "OPENAI_API_KEY",
    "ChatAnthropic": "ANTHROPIC_API_KEY",
    "ChatMistralAI": "MISTRAL_API_KEY",
    "ChatGoogle": "GOOGLE_API_KEY",
}


def safe_float(value: Any, default: float = 0.5) -> float:
    """Convert value to float or return default."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


class AIModelSettings:  # pylint: disable=too-few-public-methods
    """Constants for keys in AIModelConfig.settings."""

    API_KEY = "api_key"
    TEMPERATURE = "temperature"


class AIModelError(Exception):
    """Error in AI model."""

    def __init__(self, model_name: str, model_class: str, exception: Exception) -> None:
        error_message = str(exception)
        self.show_api_key_info = True
        if isinstance(exception, openai.APIError):
            exc_dict = exception.body
            if isinstance(exc_dict, dict) and "message" in exc_dict:
                error_message = exc_dict["message"]
                if "does not support" in error_message and "with this model" in error_message:
                    if model_name.startswith("o1-"):
                        error_message = (
                            "<br>To use o1 models you should be on Tier 2 or higher "
                            '(<a href="https://platform.openai.com/docs/guides/'
                            'rate-limits#usage-tiers">Tiers doc</a>).<br><br>'
                        )
                    else:
                        error_message = f"The model `{model_name}` is not supported in you account."
                    self.show_api_key_info = False

        self.model_name = model_name
        self.model_class = model_class
        self.error_message = error_message
        logger.error(
            f"{self.error_message}, model: {model_name}, class: {model_class}, "
            f"show_api_key_info: {self.show_api_key_info}",
        )
        super().__init__(
            f"AI class `{model_class}` error for model `{model_name}`: {error_message}",
        )


def find_nth_occurrence(substring: str, string: str, occurrence: int) -> int:
    """Find the nth occurrence (1 - first, etc) of a substring in a string."""
    start = -1
    for _ in range(occurrence):
        start = string.find(substring, start + 1)
        if start == -1:
            return -1
    return start


def _remove_word_marks(text: str) -> str:
    """Remove word marks from text but keep sentence marks."""
    for delimiter in (WORD_START_MARK, WORD_END_MARK):
        text = text.replace(delimiter, "")
    return text


def _remove_sentence_marks(text: str) -> str:
    """Remove word marks from text but keep sentence marks."""
    for delimiter in (SENTENCE_START_MARK, SENTENCE_END_MARK):
        text = text.replace(delimiter, "")
    return text


def _extract_sentence(text: str) -> str:
    """Extract marked sentence only.

    Also remove word marks.

    In many cases NLTK mark a group of sentences as one sentence.
    AI models im most cases translate only first of the marked sentences if we say
    "translated marked fragment".
    So we leave just marked sentences and say "translate the text" and that works fine.
    """
    text = _remove_word_marks(text)
    if SENTENCE_START_MARK in text:
        text = text.split(SENTENCE_START_MARK)[1]
    if SENTENCE_END_MARK in text:
        text = text.split(SENTENCE_END_MARK)[0]
    return text


class TextOutputParser(BaseOutputParser[str]):
    """Simple output parser."""

    def parse(self, text: str) -> str:
        return _remove_sentence_marks(_remove_word_marks(text))


class Llm:  # pylint: disable=too-few-public-methods
    """AI lexical articles."""

    ChatMessages = list[SystemMessage | HumanMessage | AIMessage]
    _model_cache: dict[str, Any]

    def __init__(self) -> None:
        # os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
        # os.environ["MISTRAL_API_KEY"] = os.getenv("MISTRAL_API_KEY")
        self._prompt_templates: dict[str, ChatPromptTemplate] = self._load_prompt_templates()
        self._article_pipelines_factory = self._create_article_pipelines_factory()
        self._model_cache: dict[str, Any] = {}
        self.chat_models = self._load_chat_models()

    def _load_chat_models(self) -> dict[str, dict[str, Any]]:
        yaml_path = os.path.join(settings.BASE_DIR, "lexiflux", "resources", "chat_models.yaml")
        with open(yaml_path, encoding="utf-8") as file:
            return yaml.safe_load(file)  # type: ignore

    def article_names(self) -> list[str]:
        """Return a list of all available Lexical Article names."""
        return list(self._article_pipelines_factory.keys())

    def _create_article_pipelines_factory(self) -> dict[str, Any]:
        text_parser = TextOutputParser()

        return {
            "Translate": lambda model: (
                RunnablePassthrough() | self._prompt_templates["Translate"] | model | text_parser
            ),
            "Lexical": lambda model: (
                RunnablePassthrough(text=lambda x: _remove_sentence_marks(x["text"]))
                | self._prompt_templates["Lexical"]
                | model
                | text_parser
            ),
            "Explain": lambda model: (
                RunnablePassthrough() | self._prompt_templates["Explain"] | model | text_parser
            ),
            "Origin": lambda model: (
                RunnablePassthrough() | self._prompt_templates["Origin"] | model | text_parser
            ),
            "Sentence": lambda model: (
                RunnablePassthrough.assign(text=lambda x: _extract_sentence(x["text"]))
                | self._prompt_templates["Sentence"]
                | model
                | text_parser
            ),
            "AI": lambda model: (
                RunnablePassthrough.assign(
                    messages=lambda x: [
                        SystemMessage(content=x["prompt"]),
                        HumanMessage(content=f"The text is: {x['text']}"),
                    ],
                )
                | (lambda x: model.invoke(x["messages"]))
                | text_parser
            ),
        }

    def generate_article(
        self,
        article_name: str,
        params: dict[str, Any],
        data: dict[str, Any],
    ) -> str:
        """Generate the article based on the data.

        Expects in `params`:
        - model: LLM model name from ChatModels.keys()
        - user: User object
        Expects in `data`:
        - book_code
        - book_page:
        - book_page_number:
        - text_language:
        - user_language: User's language
        - term_word_ids: list of the highlighted word IDs, expected to be contiguous

        Returns:
            HTML formatted article.

        """
        try:
            return self._generate_article_cached(
                article_name,
                self.hashable_dict(params),
                self.hashable_dict(data),
            )
        except Exception as e:
            raise AIModelError(
                params["model"],
                self.chat_models[params["model"]]["model"],
                e,
            ) from e

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
        data["article_name"] = article_name

        if article_name not in self._article_pipelines_factory:
            raise ValueError(f"Lexical article '{article_name}' not found.")

        if article_name == "AI":
            # Add the prompt to the data dictionary for the "AI" type
            data["prompt"] = params["prompt"]

        marked_text = self.mark_term_and_sentence(hashable_data)
        data["text"] = extract_content_from_html(marked_text)
        data["detected_language"] = data["text_language"]  # todo: actually detect the language

        model = self._get_or_create_model(params)
        pipeline = self._article_pipelines_factory[article_name](model)

        logger.info(data)
        return pipeline.invoke(data)  # type: ignore

    def _load_prompt_templates(self) -> dict[str, ChatPromptTemplate]:
        prompts = {}
        prompt_dir = os.path.join(settings.BASE_DIR, "lexiflux", "resources", "prompts")

        for filename in os.listdir(prompt_dir):
            if filename.endswith(".txt"):
                article_name = os.path.splitext(filename)[0]
                file_path = os.path.join(prompt_dir, filename)

                with open(file_path, encoding="utf8") as file:
                    prompt_text = file.read().strip()

                prompts[article_name] = ChatPromptTemplate.from_messages(
                    [("system", prompt_text), ("user", "The text is: {text}")],
                )

        return prompts

    def detect_term_words(
        self,
        text: str,
        term: str,
        term_occurence: int = 1,
        lang_code: str = "en",
    ) -> dict[str, Any]:
        """In the text given detect word slices and term words.

        For debugging plain text without book page.

        If term is included in the text multiple times, you can specify which occurrence to use
        (1 - 1st, etc).

        Return: dict with "term_word_ids" and "word_slices" ready to use in generate_article().
        """
        word_slices, _ = parse_words(text, lang_code=lang_code)
        term_start = find_nth_occurrence(term, text, term_occurence)
        term_end = term_start + len(term)
        # find the word slices that contain the term
        term_word_ids = []
        for i, (start, end) in enumerate(word_slices):
            if start >= term_start and end <= term_end:
                term_word_ids.append(i)

        return {
            "word_slices": word_slices,
            "term_word_ids": term_word_ids,
        }

    def mark_term_and_sentence(  # pylint: disable=too-many-locals
        self,
        hashable_data: tuple[tuple[str, Any], ...],
        context_words: int = 10,
    ) -> str:
        """Mark in the text the term and sentence(s) that contains it.

        Includes in result full sentences with at least 'context_words' before and after the term.
        Only the sentence(s) containing the term is marked as `sentence(s)`.

        Expects in `data`:
        - book_code:
        - book_page_number:
        - term_word_ids:
            list of the highlighted word IDs, expected to be contiguous

        Returns:
            full sentences context with the term's sentence(s) marked
            with SENTENCE_START_MARK and SENTENCE_END_MARK
            and term marked with WORD_START_MARK and WORD_END_MARK

        """
        data = dict(hashable_data)
        book = Book.objects.get(code=data["book_code"])
        page = BookPage.objects.get(book=book, number=data["book_page_number"])
        term_word_ids: list[int] = data["term_word_ids"]

        text = page.content
        word_slices = page.words
        mapping = page.word_sentence_mapping

        # Find the sentence(s) containing the term
        start_term_sentence_id = mapping[term_word_ids[0]]
        end_term_sentence_id = mapping[term_word_ids[-1]]

        sentence_word_ids = [
            word_id
            for word_id, sentence_id in mapping.items()
            if start_term_sentence_id <= sentence_id <= end_term_sentence_id
            and 0 <= word_id < len(word_slices)
        ]
        sentence_start = word_slices[min(sentence_word_ids)][0]
        sentence_end = word_slices[max(sentence_word_ids)][1]

        # Find the range of words to include in the broader context
        start_context_word_id = max(0, term_word_ids[0] - context_words)
        end_context_word_id = min(len(word_slices) - 1, term_word_ids[-1] + context_words)

        # Expand to full sentences for the context
        start_context_sentence_id = mapping[start_context_word_id]
        end_context_sentence_id = mapping[end_context_word_id]

        full_sentences_context_word_ids = [
            word_id
            for word_id, sentence_id in mapping.items()
            if start_context_sentence_id <= sentence_id <= end_context_sentence_id
            and 0 <= word_id < len(word_slices)
        ]

        full_sentences_context_start = word_slices[min(full_sentences_context_word_ids)][0]
        full_sentences_context_end = word_slices[max(full_sentences_context_word_ids)][1]

        # Mark only the sentence containing the term
        marked_text = (
            f"{text[full_sentences_context_start:sentence_start]}{SENTENCE_START_MARK}"
            f"{text[sentence_start:sentence_end]}{SENTENCE_END_MARK}"
            f"{text[sentence_end:full_sentences_context_end]}"
        )

        # Adjust term_start and term_end to account for the added SENTENCE_START_MARK
        term_start = (
            word_slices[term_word_ids[0]][0]
            + len(SENTENCE_START_MARK)
            - full_sentences_context_start
        )
        term_end = (
            word_slices[term_word_ids[-1]][1]
            + len(SENTENCE_START_MARK)
            - full_sentences_context_start
        )

        # Mark the term within the context
        return (
            f"{marked_text[:term_start]}{WORD_START_MARK}"
            f"{marked_text[term_start:term_end]}{WORD_END_MARK}"
            f"{marked_text[term_end:]}"
        )

    def get_model_settings(self, user: CustomUser, model_class: str) -> dict[str, Any]:
        """Get AI model settings for the given user and model"""
        ai_model_config = AIModelConfig.get_or_create_ai_model_config(user, model_class)
        return ai_model_config.settings.copy()

    def _get_or_create_model(self, params: dict[str, Any]) -> Any:
        """Get or create AI model instance.

        in params["user"] - CustomUser object
        """
        model_name = params["model"]
        user = params["user"]
        model_key = f"{model_name}_{user.id}"

        if model_key not in self._model_cache:
            model_info = self.chat_models.get(model_name)
            if not model_info:
                raise ValueError(f"Unsupported model: {model_name}")

            model_class = model_info["model"]
            try:
                model_settings = self.get_model_settings(user, model_class)
                common_params = {
                    "temperature": safe_float(
                        model_settings.get(AIModelSettings.TEMPERATURE, 0.5),
                    ),
                }

                if model_class == "ChatOpenAI":
                    self._model_cache[model_key] = ChatOpenAI(  # type: ignore
                        model=model_name,
                        api_key=model_settings.get(AIModelSettings.API_KEY),
                        **common_params,  # type: ignore
                    )
                elif model_class == "Ollama":
                    self._model_cache[model_key] = Ollama(  # pylint: disable=not-callable
                        model=model_name,
                        **common_params,
                    )
                elif model_class == "ChatAnthropic":
                    api_key = model_settings.get(AIModelSettings.API_KEY)
                    if api_key:
                        # If we have an API key from database, use it explicitly
                        self._model_cache[model_key] = ChatAnthropic(
                            model=model_name,  # type: ignore
                            api_key=api_key,  # type: ignore
                            **common_params,  # type: ignore
                        )
                    else:
                        # Let Anthropic SDK auto-load from ANTHROPIC_API_KEY environment variable
                        self._model_cache[model_key] = ChatAnthropic(
                            model=model_name,  # type: ignore
                            **common_params,  # type: ignore
                        )
                elif model_class == "ChatGoogle":
                    self._model_cache[model_key] = ChatGoogleGenerativeAI(  # type: ignore
                        model=model_name,
                        google_api_key=model_settings.get(AIModelSettings.API_KEY),
                        temperature=common_params["temperature"],
                    )
                elif model_class == "ChatMistralAI":
                    self._model_cache[model_key] = ChatMistralAI(
                        api_key=model_settings.get(AIModelSettings.API_KEY),
                        **common_params,  # type: ignore
                    )
                else:
                    raise ValueError(f"Unsupported model class: {model_class}")
            except Exception as e:
                raise AIModelError(model_name, model_class, e) from e
        return self._model_cache[model_key]

    def hashable_dict(self, d: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
        """Convert a dictionary to a hashable tuple."""

        def make_hashable(v: Any) -> Any:
            if isinstance(v, dict):
                return self.hashable_dict(v)
            # __hash__ method of Django model objects uses id so it's fine
            return tuple(make_hashable(i) for i in v) if isinstance(v, list) else v

        return tuple((k, make_hashable(v)) for k, v in sorted(d.items()))
