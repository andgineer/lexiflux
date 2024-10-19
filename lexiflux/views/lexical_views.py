"""Views for the translation and lexical sidebar."""

import urllib.parse
from typing import List, Dict, Any

from django.http import HttpRequest, HttpResponse, JsonResponse

from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
import django.utils.timezone

from pydantic import Field

from lexiflux.lexiflux_settings import settings
from lexiflux.decorators import smart_login_required
from lexiflux.api import ViewGetParamsModel, get_params
from lexiflux.language.parse_html_text_content import extract_content_from_html
from lexiflux.language.llm import (
    Llm,
    AIModelError,
    SENTENCE_START_MARK,
    SENTENCE_END_MARK,
    WORD_START_MARK,
    WORD_END_MARK,
)
from lexiflux.language.translation import get_translator
from lexiflux.models import BookPage, LanguagePreferences, Book, CustomUser, TranslationHistory

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


def get_llm_errors_folder() -> str:
    """Get the folder for LLM errors."""
    return "llm-error" if settings.lexiflux.ui_settings_only else "llm-error-env"


def get_lexical_article(  # pylint: disable=too-many-positional-arguments,too-many-arguments,too-many-locals
    article_name: str,
    article_params: Dict[str, Any],
    selected_text: str,
    book_page: BookPage,
    term_word_ids: List[int],
    language_preferences: LanguagePreferences,
    user: CustomUser,
) -> Dict[str, Any]:
    """Get the lexical article.

    Return {"article": str, "error": bool} dictionary.
    """
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

    try:
        llm = Llm()
        data = llm.generate_article(
            article_name=article_name,
            params={**article_params, "user": user},
            data={
                "book_code": book_page.book.code,
                "book_page_number": book_page.number,
                "user_language": language_preferences.user_language.google_code,
                "term_word_ids": term_word_ids,
                "text_language": book_page.book.language.google_code,
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
def translate(request: HttpRequest, params: TranslateGetParams) -> HttpResponse:  # pylint: disable=too-many-locals
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
    term_text = extract_content_from_html(
        book_page.content[
            book_page.words[term_word_ids[0]][0] : book_page.words[term_word_ids[-1]][1]
        ]
    )

    if term_text.strip() == "":
        return JsonResponse({"error": "Selected text is empty"}, status=400)

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

        # Create or update TranslationHistory instance
        context = get_context_for_translation_history(book, book_page, term_word_ids)
        translation_history, created = TranslationHistory.objects.update_or_create(
            term=term_text,
            source_language=book.language,
            user=request.user,
            defaults={
                "translation": result["article"],
                "target_language": language_preferences.user_language,
                "context": context,
                "book": book,
            },
        )
        if not created:
            translation_history.lookup_count += 1
            translation_history.last_lookup = django.utils.timezone.now()
            translation_history.save()

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


def get_context_for_translation_history(
    book: Book, book_page: BookPage, term_word_ids: List[int]
) -> str:
    """Get the context for the term to save in Translation History.

    Surround the sentence with the term with {CONTEXT_MARK}.

    Replace the term inside it with single {CONTEXT_MARK}.
    """
    llm = Llm()
    data = {
        "book_code": book.code,
        "book_page_number": book_page.number,
        "term_word_ids": term_word_ids,
    }
    marked_context = llm.mark_term_and_sentence(llm.hashable_dict(data), context_words=10)

    # Replace sentence marks with CONTEXT_MARK
    context = marked_context.replace(SENTENCE_START_MARK, TranslationHistory.CONTEXT_MARK)
    context = context.replace(SENTENCE_END_MARK, TranslationHistory.CONTEXT_MARK)

    # Replace the marked words (including surrounding marks) with a single CONTEXT_MARK
    start_index = context.find(WORD_START_MARK)
    end_index = context.find(WORD_END_MARK, start_index) + len(WORD_END_MARK)
    context = context[:start_index] + TranslationHistory.CONTEXT_MARK + context[end_index:]

    return context  # type: ignore
