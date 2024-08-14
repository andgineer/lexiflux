"""Views for the translation and lexical sidebar."""

import urllib.parse
from typing import List, Tuple, Dict, Any

from django.http import HttpRequest, HttpResponse, JsonResponse

from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string

from pydantic import Field

from lexiflux.lexiflux_settings import settings
from lexiflux.decorators import smart_login_required
from lexiflux.api import ViewGetParamsModel, get_params
from lexiflux.language.parse_html_text_content import extract_content_from_html
from lexiflux.language.llm import Llm, AIModelError
from lexiflux.language.translation import get_translator
from lexiflux.models import BookPage, LanguagePreferences, Book, CustomUser

MAX_SENTENCE_LENGTH = 100


class TranslateGetParams(ViewGetParamsModel):
    """GET params for the /translate."""

    word_ids: str = Field(default=None)
    book_code: str = Field(..., min_length=1)
    book_page_number: int = Field(..., ge=1)
    lexical_article: str = Field(
        ...,
        description="Lexical article index. '0' for inline, "
        "otherwise number of the panel in Sidebar",
    )


def get_context_for_term(
    book_page: BookPage, term_word_ids: List[int]
) -> Tuple[str, List[Tuple[int, int]], List[int], int]:
    """Get the context for the term."""
    start_word = max(0, term_word_ids[0] - MAX_SENTENCE_LENGTH)
    end_word = term_word_ids[-1] + MAX_SENTENCE_LENGTH
    if end_word - start_word < MAX_SENTENCE_LENGTH * 2:
        end_word = start_word + MAX_SENTENCE_LENGTH * 2
    end_word = min(end_word, len(book_page.words))
    if end_word - start_word < MAX_SENTENCE_LENGTH * 2:
        start_word = max(0, end_word - MAX_SENTENCE_LENGTH * 2)

    context_str, context_word_slices = book_page.extract_words(start_word, end_word)
    context_term_word_ids = [word_id - start_word for word_id in term_word_ids]
    return context_str, context_word_slices, context_term_word_ids, start_word


def get_llm_errors_folder() -> str:
    """Get the folder for LLM errors."""
    return "llm-error" if settings.lexiflux.ui_settings_only else "llm-error-env"


def get_lexical_article(  # pylint: disable=too-many-arguments, too-many-locals
    article_name: str,
    article_params: Dict[str, Any],
    selected_text: str,
    book_page: BookPage,
    term_word_ids: List[int],
    language_preferences: LanguagePreferences,
    user: CustomUser,
) -> Dict[str, Any]:
    """Get the lexical article."""
    if article_name == "Site":
        return {
            "url": article_params.get("url", "").format(
                term=urllib.parse.quote(selected_text),
                lang=book_page.book.language.name.lower(),
                langCode=book_page.book.language.google_code,
                toLang=language_preferences.user_language.name.lower(),
                toLangCode=language_preferences.user_language.google_code,
            ),
            "window": article_params.get("window", True),
        }

    if article_name == "Dictionary":
        translator = get_translator(
            article_params["dictionary"],
            book_page.book.language.name.lower(),
            language_preferences.user_language.name.lower(),
        )
        return {"article": translator.translate(selected_text)}

    context_str, context_word_slices, context_term_word_ids, context_start_word = (
        get_context_for_term(book_page, term_word_ids)
    )
    try:
        llm = Llm()
        data = llm.generate_article(
            article_name=article_name,
            params={**article_params, "user": user},
            data={
                "text": context_str,
                "word_slices": context_word_slices,
                "term_word_ids": context_term_word_ids,
                "text_language": book_page.book.language.google_code,
                "user_language": language_preferences.user_language.google_code,
                "book_code": book_page.book.code,
                "book_page_number": book_page.number,
                "context_start_word": context_start_word,
            },
        )
        return {"article": str(data)}
    except AIModelError as e:
        error_template_folder = get_llm_errors_folder()
        try:
            error_message = render_to_string(
                f"{error_template_folder}/{e.model_class}.html",
                {"model_name": e.model_name, "error_message": e.error_message},
            )
        except TemplateDoesNotExist:
            # Fallback to generic error template if specific template doesn't exist
            error_message = render_to_string(
                f"{error_template_folder}/generic_error.html",
                {
                    "model_class": e.model_class,
                    "model_name": e.model_name,
                    "error_message": e.error_message,
                },
            )
        return {"article": error_message, "error": True}
    except Exception as e:  # pylint: disable=broad-except
        return {"article": f"An error occurred: {e}", "error": True}


@smart_login_required
@get_params(TranslateGetParams)
def translate(request: HttpRequest, params: TranslateGetParams) -> HttpResponse:
    """Translate the selected text.

    The selected text is defined by the word IDs.
    If the lexical article is provided, the article is generated for the selected text.
    """
    book = Book.objects.get(code=params.book_code)
    book_page = BookPage.objects.get(book=book, number=params.book_page_number)

    language_preferences = LanguagePreferences.get_or_create_language_preferences(
        request.user, book.language
    )

    term_word_ids = [int(id) for id in params.word_ids.split(".")]
    # term_words = " ".join(
    #     [
    #         book_page.content[book_page.words[id][0] : book_page.words[id][1]]
    #         for id in term_word_ids
    #     ]
    # )
    term_text = extract_content_from_html(
        book_page.content[
            book_page.words[term_word_ids[0]][0] : book_page.words[term_word_ids[-1]][1]
        ]
    )

    result: Dict[str, Any] = {}

    if int(params.lexical_article) == 0:
        article_type = language_preferences.inline_translation_type
        article_parameters = language_preferences.inline_translation_parameters
        result.update(
            get_lexical_article(
                article_type,
                article_parameters,
                term_text,
                book_page,
                term_word_ids,
                language_preferences,
                request.user,
            )
        )
        result["article"] = result["article"].split("<hr>")[0]

    else:
        all_articles = language_preferences.lexical_articles.all()
        article_index = int(params.lexical_article) - 1

        if 0 <= article_index < len(all_articles):
            article = all_articles[article_index]
            result.update(
                get_lexical_article(
                    article.type,
                    article.parameters,
                    term_text,
                    book_page,
                    term_word_ids,
                    language_preferences,
                    request.user,
                )
            )
        else:
            return JsonResponse({"error": "Lexical article not found"}, status=404)

    print(f"Result: {result}")
    return JsonResponse(result)
