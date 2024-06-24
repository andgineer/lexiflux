"""AI lexical articles."""

import os
from functools import lru_cache
from typing import Any, Dict, List

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
import openai
from langchain.schema import BaseOutputParser


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
        class SimpleOutputParser(BaseOutputParser[str]):
            """Simple output parser."""

            def parse(self, text: str) -> str:
                return text

        parser = SimpleOutputParser()

        translation_system_template = """Given the following text in {text_language},
        translate the term marked as with <span> tag from {text_language} to {user_language}. 
        Give translation for the exact sentence where the term is (and not all occurrences in the text).
        If you are sure the text is in a different language, translate from that language and indicate it by starting the result with the detected language name in parentheses.
        Put into result only word translation without surrounding <b></b>."""

        translation_prompt_template = ChatPromptTemplate.from_messages(
            [("system", translation_system_template), ("user", "{text}")]
        )

        dictionary_system_template = """Given the following text in {text_language},
        write {text_language} - {user_language} dictionary article for the term marked with <span> tag.
        The article should be in {user_language}.
        Include grammar attributes - part of the speech, genre, number, countability and other grammar attributes.
        All grammar attributes should be on one line in a compact way like in good dictionaries.
        Include different meanings, declination table and other information you expect to see in a good dictionary like Oxford, but do not include examples.
        If you are sure the text is in a different language, write the article based on that language and indicate it by starting the result with the detected language name in parentheses.
        Give the result in HTML formatting, without any block marks."""

        dictionary_prompt_template = ChatPromptTemplate.from_messages(
            [("system", dictionary_system_template), ("user", "{text}")]
        )

        examples_system_template = """Given the following text in {text_language},
provide up to seven examples in {text_language} of sentences with the term marked with <span> tag in its meaning in the exact 
sentence where the term is marked with <span> tag.
Do not give as an example the usages in the given text.
Give translations of the examples to {user_language}, do not prefix them with the language name.
If you are sure the text is not in a {text_language}, provide examples based on that detected language.
Ensure that the detected language is clearly stated at the beginning of the examples list e.g., (Latin) but only if it is different from {text_language}.
Put examples into separate paragraphs (<p>).
Give the result in HTML formatting, without any block marks.

Ensure your response adheres strictly to these instructions:
- do not repeat examples.
- if you detected language different from {text_language} then examples should be in that language

Examples:
1) Serbian - English
Text: Abbati, medico, patronoque <span>intima pande</span>.

(Latin)

<p>Puella matri suae <span>intima pande</span>.</p>
<p>Girl, reveal your innermost thoughts to your mother.</p>

<p>Amico fideli omnia <span>intima pande</span>.</p>
<p>Reveal your deepest secrets to a faithful friend.</p>

<p>Sapienti semper <span>intima pande</span>.</p>
<p>Always reveal your innermost thoughts to a wise person.</p>

<p>In angustiis veritas <span>intima pande</span>.</p>
<p>In difficulties, reveal the truth within.</p>

<p>Omnibus rebus consideratis, <span>intima pande</span>.</p>
<p>After considering all things, reveal your innermost thoughts.</p>

<p>Quando confidas, <span>intima pande</span>.</p>
<p>When you trust, reveal your innermost thoughts.</p>

<p>Magistro tuo veritatem <span>intima pande</span>.</p>
<p>Reveal the truth to your teacher.</p>

2) Serbian - English
"text": "pokreće sve. <span>list</span> sa drveta je pao na zemlju. Na stolu je bio list papira sa važnim beleškama. Ljubav je najlepša ",

<p>Jesen je donela prvi opali <span>list</span>.</p>
<p>Autumn brought the first fallen leaf.</p>

<p>Čuo sam kako <span>list</span> šuška pod mojim nogama.</p>
<p>I heard the leaf rustling under my feet.</p>

<p>Na trgu je vetar podigao suvi <span>list</span>.</p>
<p>In the square, the wind lifted a dry leaf.</p>

<p>Pročitao sam sve što je bilo napisano na tom <span>listu</span>.</p>
<p>I read everything that was written on that sheet.</p>

<p>Učitelj je dao učeniku prazan <span>list</span> papira.</p>
<p>The teacher gave the student a blank sheet of paper.</p>

<p>Svaki <span>list</span> u knjizi je bio pažljivo ispisan.</p>
<p>Every page in the book was carefully written.</p>

<p>Stari <span>list</span> se jedva držao za granu.</p>
<p>The old leaf was barely hanging on the branch.</p>

        """

        examples_prompt_template = ChatPromptTemplate.from_messages(
            [("system", examples_system_template), ("user", "{text}")]
        )

        explain_system_template = """You are a {text_language} teacher.
Explain to your {user_language} student, using only {text_language}, the meaning of the term marked in the text with a <span> tag.
Explain only in the context of the sentence where the term is marked with <span> tag.
If the text is not in {text_language}, start with the detected language in parentheses. 
After <hr> provide the translation of the explanation to {user_language}.
Give the result in HTML formatting without any additional block marks or labels.

Ensure your response adheres strictly to these instructions:
- Use {text_language} for the initial explanation.
- Never put into the result ({text_language}) or ({user_language}).

Examples:
1)
Serbian teacher, English student
Text: Postepeno – očito, od umora – njegov govor je sve očiglednije poprimao <span>mačji</span> akcenat
Result:
"Mačji" se odnosi na nešto što je povezano sa mačkama. Na primer, mačji akcenat znači da osoba govori na način koji podseća na zvukove 
koje mačke proizvode.
<hr>
"Mačji" refers to something that is related to cats. For example, a "mačji akcenat" (cat accent) means that a person speaks in a 
way that resembles the sounds that cats make.

1)
Serbian teacher, English student
Text: Abbati, medico, patronoque <span>intima pande</span>.
(Latin) "Intima pande" je latinski izraz koji se može prevesti kao "otkrijte najdublje tajne" ili "otkrijte najintimnije detalje".

"Intima" znači "najdublje" ili "najintimnije".
"Pande" je imperativ glagola "pandere", što znači "otkriti" ili "razotkriti".

U kontekstu cele fraze, ovo se verovatno odnosi na ideju da treba otkriti svoje najdublje misli ili tajne svešteniku (abbati), lekaru 
(medico) i zaštitniku ili pokrovitelju (patrono). Ova fraza sugeriše da bi ove tri figure trebalo da budu osobe od poverenja kojima 
se mogu poveriti najintimnije informacije.
<hr>
"Intima pande" is a Latin expression that can be translated as "reveal the deepest secrets" or "disclose the most intimate details".

"Intima" means "deepest" or "most intimate".
"Pande" is the imperative form of the verb "pandere", which means "to reveal" or "to disclose".

In the context of the whole phrase, this likely refers to the idea that one should reveal their deepest thoughts or secrets to the abbot 
(abbati), the doctor (medico), and the patron or protector (patrono). This phrase suggests that these three figures should be trusted 
individuals to whom one can confide the most intimate information.
"""

        explain_prompt_template = ChatPromptTemplate.from_messages(
            [("system", explain_system_template), ("user", "{text}")]
        )

        return {
            "Translate": {"template": translation_prompt_template, "parser": parser},
            "Dictionary": {"template": dictionary_prompt_template, "parser": parser},
            "Examples": {"template": examples_prompt_template, "parser": parser},
            "Explain": {"template": explain_prompt_template, "parser": parser},
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
