"""AI generated lexical articles."""

import os
from functools import lru_cache
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import openai
from langchain.schema import BaseOutputParser


class Llm:  # pylint: disable=too-few-public-methods
    """AI lexical articles."""

    def __init__(self) -> None:
        openai.api_key = os.getenv("OPENAI_API_KEY")
        # alternatively set LANGCHAIN_API_KEY

        # gpt-4-turbo - more correct grammar info
        self.gpt35 = ChatOpenAI(
            model="gpt-3.5-turbo",
            api_key=os.getenv("OPENAI_API_KEY"),  # type: ignore
        )
        self.gpt4 = ChatOpenAI(
            model="gpt-4-turbo",
            api_key=os.getenv("OPENAI_API_KEY"),  # type: ignore
        )

        self.pipelines = self._create_pipelines()

    def _create_pipelines(self) -> Dict[str, Any]:
        class SimpleOutputParser(BaseOutputParser[str]):
            """Simple output parser."""

            def parse(self, text: str) -> str:
                return text

        parser = SimpleOutputParser()

        translation_system_template = """Given the following text in {source_language},
        translate the word marked as <b>{word}</b> from {source_language} to {target_language}. 
        Give the meaning of it in the exact sentence.
        Put into result only word translation without surrounding <b></b>"""

        translation_prompt_template = ChatPromptTemplate.from_messages(
            [("system", translation_system_template), ("user", "{text}")]
        )

        dictionary_system_template = """Given the following text in {source_language},
        write {source_language} - {target_language} dictionary article for the word marked as <b>{word}</b>.
        The article should be in {target_language}.
        Include grammar attributes - part of the speech, genre, number, countability and other grammar attributes.
        All grammar attributes should be on one line in a compact way like in good dictionaries.
        Include different meanings, declination table and other information you expect to see in a good dictionary like Oxford, but do not include examples.
        And do not include translation of the text provided.
        Give the result in HTML formatting, without any block marks."""

        dictionary_prompt_template = ChatPromptTemplate.from_messages(
            [("system", dictionary_system_template), ("user", "{text}")]
        )

        examples_system_template = """Given the following text in {source_language},
        provide at least seven examples in {source_language} of sentences using the word marked as <b>{word}</b> in his meaning in the sentence.
        Do not give as an example the usage in the given text.
        Give translations of the examples to {target_language}
        Each example in a separate paragraph (<p>).
        Give the result in HTML formatting, without any block marks.
        """

        examples_prompt_template = ChatPromptTemplate.from_messages(
            [("system", examples_system_template), ("user", "{text}")]
        )

        explanation_system_template = """Given the following text in {source_language},
        using only {source_language} explain the meaning of the word marked as <b>{word}</b> in exact sentence.
        You are a teacher who read the text with your student, use the exact context in the sentence for the explanation.
        """

        explanation_prompt_template = ChatPromptTemplate.from_messages(
            [("system", explanation_system_template), ("user", "{text}")]
        )

        return {
            "Translate": translation_prompt_template | self.gpt35 | parser,
            "Dictionary": dictionary_prompt_template | self.gpt35 | parser,
            "Dictionary Advanced": dictionary_prompt_template | self.gpt4 | parser,
            "Examples": examples_prompt_template | self.gpt35 | parser,
            "Explain": explanation_prompt_template | self.gpt35 | parser,
        }

    @lru_cache(maxsize=1000)
    def run_pipeline(  # pylint: disable=too-many-arguments
        self, pipeline_name: str, text: str, word: str, source_language: str, target_language: str
    ) -> str:
        """Run pipeline."""
        if pipeline_name not in self.pipelines:
            raise ValueError(f"Pipeline '{pipeline_name}' not found.")

        params = {
            "text": text,
            "word": word,
            "source_language": source_language,
            "target_language": target_language,
        }

        return self.pipelines[pipeline_name].invoke(params)  # type: ignore
