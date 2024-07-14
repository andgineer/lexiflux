"""AI lexical articles."""

import os
import traceback
from functools import lru_cache
from typing import Any, Dict, List, Tuple, Callable

from django.conf import settings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_mistralai import ChatMistralAI
from langchain_community.llms import Ollama  # pylint: disable=no-name-in-module

import openai
from langchain.schema import BaseOutputParser

from lexiflux.language.sentence_extractor_llm import (
    SENTENCE_START_MARK,
    SENTENCE_END_MARK,
    WORD_START_MARK,
    WORD_END_MARK,
)
from lexiflux.language.word_extractor import parse_words
from lexiflux.models import BookPage, Book

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
    # "zephyr": {
    #     "title": "Zephyr 7B",
    #     "model": Ollama,
    #     "suffix": "🌬️7B",
    # },
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


def substitute_marks(template: str) -> str:
    """Substitute mark names with actual mark."""
    return (
        template.replace("[SENTENCE_START]", SENTENCE_START_MARK)
        .replace("[SENTENCE_END]", SENTENCE_END_MARK)
        .replace("[WORD_START]", WORD_START_MARK)
        .replace("[WORD_END]", WORD_END_MARK)
    )


def remove_marks(text: str) -> str:
    """Remove sentence and word marks from text."""
    for delimiter in (
        SENTENCE_START_MARK,
        SENTENCE_END_MARK,
        WORD_START_MARK,
        WORD_END_MARK,
    ):
        text = text.replace(delimiter, "")
    return text


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


class TextOutputParser(BaseOutputParser[str]):
    """Simple output parser."""

    def parse(self, text: str) -> str:
        return remove_marks(text)


class Llm:  # pylint: disable=too-few-public-methods
    """AI lexical articles."""

    ChatMessages = List[SystemMessage | HumanMessage | AIMessage]
    _model_cache: Dict[str, Any]

    def __init__(self) -> None:
        openai.api_key = os.getenv("OPENAI_API_KEY")
        # os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY")
        # os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
        # os.environ["MISTRAL_API_KEY"] = os.getenv("MISTRAL_API_KEY")
        self._prompt_templates: Dict[str, ChatPromptTemplate] = self._load_prompt_templates()
        self._article_pipelines_factory = self._create_article_pipelines_factory()
        self._model_cache: Dict[str, Any] = {}

    def article_names(self) -> List[str]:
        """Return a list of all available Lexical Article names."""
        return list(self._article_pipelines_factory.keys())

    def _create_article_pipelines_factory(self) -> Dict[str, Callable[[Any], ChatMessages]]:
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
            "Sentence": lambda model: (
                RunnablePassthrough.assign(text=lambda x: _remove_word_marks(x["text"]))
                | self._prompt_templates["Sentence"]
                | model
                | text_parser
            ),
        }

    def generate_article(
        self, article_name: str, params: Dict[str, Any], data: Dict[str, Any]
    ) -> str:
        """Generate the article based on the data.

        Expects in `params`:
        - model: LLM model name from ChatModels.keys()
        Expects in `data`:
        - book_page:
        - book_page_number:
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
        data["model"] = params["model"]

        if article_name not in self._article_pipelines_factory:
            raise ValueError(f"Lexical article '{article_name}' not found.")

        marked_text = self.mark_term_and_sentence(hashable_data)
        data["text"] = marked_text["text"]
        data["detected_language"] = marked_text["detected_language"]

        model = self._get_or_create_model(data)
        pipeline = self._article_pipelines_factory[article_name](model)

        return pipeline.invoke(data)  # type: ignore

    def _load_prompt_templates(self) -> Dict[str, ChatPromptTemplate]:
        prompts = {}
        prompt_dir = os.path.join(settings.BASE_DIR, "lexiflux", "resources", "prompts")

        for filename in os.listdir(prompt_dir):
            if filename.endswith(".txt"):
                article_name = os.path.splitext(filename)[0]
                file_path = os.path.join(prompt_dir, filename)

                with open(file_path, "r", encoding="utf8") as file:
                    prompt_text = substitute_marks(file.read().strip())

                prompts[article_name] = ChatPromptTemplate.from_messages(
                    [("system", prompt_text), ("user", "The text is: {text}")]
                )

        return prompts

    def detect_term_words(
        self,
        text: str,
        term: str,
        term_occurence: int = 1,
    ) -> Dict[str, Any]:
        """In the text given detect word slices and term words.

        For debugging plain text without book page.

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
        - book_code:
        - book_page_number:
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
        book = Book.objects.get(code=data["book_code"])
        page = BookPage.objects.get(book=book, number=data["book_page_number"])
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

    def _get_or_create_model(self, data: Dict[str, Any]) -> Any:
        article_name = data["article_name"]
        text_language = data["text_language"]
        user_language = data["user_language"]
        model_name = data["model"]
        model_key = self._get_model_key(article_name, text_language, user_language, model_name)

        if model_key not in self._model_cache:
            model_info = ChatModels.get(model_name)
            if not model_info:
                raise ValueError(f"Unsupported model: {model_name}")

            model_class = model_info["model"]
            try:
                if model_class == ChatOpenAI:
                    self._model_cache[model_key] = model_class(
                        model=model_name,
                        temperature=0.5,
                        api_key=os.getenv("OPENAI_API_KEY"),
                    )
                elif model_class == Ollama:
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
            except Exception as e:
                print(f"Error creating model {model_class.__name__}({model_name}): {e}")
                print(traceback.format_exc())
                raise

        return self._model_cache[model_key]

    def _hashable_dict(self, d: Dict[str, Any]) -> Tuple[Tuple[str, Any], ...]:
        return tuple((k, tuple(v) if isinstance(v, list) else v) for k, v in sorted(d.items()))
