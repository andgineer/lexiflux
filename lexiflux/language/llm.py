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

from lexiflux.language.sentence_extractor import break_into_sentences
from lexiflux.language.word_extractor import parse_words

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
    _model_cache: Dict[str, Any]

    def __init__(self) -> None:
        openai.api_key = os.getenv("OPENAI_API_KEY")
        # os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY")
        # os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
        # os.environ["MISTRAL_API_KEY"] = os.getenv("MISTRAL_API_KEY")
        self._articles_templates = self._create_article_templates()
        self._model_cache: Dict[str, Any] = {}

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
        article_name: str,  # pylint: disable=unused-argument
        hashable_params: tuple[tuple[str, Any]],  # pylint: disable=unused-argument
        hashable_data: tuple[tuple[str, Any]],
    ) -> Dict[str, str]:
        """Return detected sentence for the first word in the `term`.

        If the sentence is not detected, it will be detected and returned.
        """
        data = dict(hashable_data)
        text_language = data["text_language"]
        text = data["text"]
        word_ids = data["word_ids"]
        term = data["term"]

        # Find the first word of the term in the text
        term_start = text.find(term)
        if term_start == -1:
            raise ValueError(f"Term '{term}' not found in the text.")

        # Find the word_id that corresponds to the start of the term
        highlighted_word_id = next(
            (i for i, (start, end) in enumerate(word_ids) if start == term_start), None
        )
        if highlighted_word_id is None:
            raise ValueError(f"No word_id found for term '{term}'.")

        # Use break_into_sentences to detect the sentence
        sentences, _ = break_into_sentences(
            text, word_ids, highlighted_word_id, lang_code=text_language
        )

        if not sentences:
            raise ValueError("No sentence detected.")

        # Get the detected sentence
        detected_sentence = sentences[0]

        # Prepare the result
        result = {
            "text": f"||{detected_sentence}||",
            "detected_language": text_language,  # do not detected language
        }

        return result

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
                    api_key=os.getenv("OPENAI_API_KEY"),
                )
            elif model_class == ChatAnthropic:
                self._model_cache[model_key] = model_class(
                    model=model_name,
                    temperature=0.5,
                )
            elif model_class == ChatGoogleGenerativeAI:
                self._model_cache[model_key] = model_class(
                    model=model_name,
                    temperature=0.5,
                )
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

    def get_article_from_text(  # pylint: disable=too-many-arguments, too-many-locals
        self,
        article_name: str,  # pylint: disable=unused-argument
        text: str,
        text_language: str,
        user_language: str,
        term_word_indices: List[int],
        model_name: str = "gpt-3.5-turbo",
    ) -> str:
        """Get the article based on the text and term word indices.

        Convenient way to debug the LLM without BookPage.
        """
        word_ids, _ = parse_words(text)

        # Find the start and end indices of the term
        term_start = word_ids[term_word_indices[0]][0]
        term_end = word_ids[term_word_indices[-1]][1]
        term = text[term_start:term_end]
        print(f"term: {term}")

        sentences, word_to_sentence = break_into_sentences(text, word_ids, lang_code=text_language)
        print(f"sentences: {sentences}")

        # Find sentences that include all words in the term
        term_sentence_indices = set()
        for word_index in term_word_indices:
            sentence_index = word_to_sentence[word_index]
            term_sentence_indices.add(sentence_index)

        # Ensure all term words are in adjacent sentences
        if max(term_sentence_indices) - min(term_sentence_indices) + 1 != len(
            term_sentence_indices
        ):
            raise ValueError("Term words are not in adjacent sentences")

        # Get the relevant sentences
        start_sentence_index = min(term_sentence_indices)
        end_sentence_index = max(term_sentence_indices)
        relevant_sentences = sentences[start_sentence_index : end_sentence_index + 1]

        # Create marked text
        marked_text = text
        # Replace the relevant sentences with marked versions
        relevant_text = "".join(relevant_sentences)
        marked_relevant_text = f"||{relevant_text.replace(term, f'**{term}**')}||"
        marked_text = marked_text.replace(relevant_text, marked_relevant_text)

        # Prepare data for the LLM chain
        data = {
            "text": marked_text,
            "term": term,
            "text_language": text_language,
            "user_language": user_language,
            "detected_language": text_language,  # do not detected language
        }

        # Use the existing method to get the article
        params = {"model": model_name}
        return self._get_article_cached(
            article_name, self._hashable_dict(params), self._hashable_dict(data)
        )
