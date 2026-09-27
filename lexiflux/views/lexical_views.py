"""Views for the translation and lexical sidebar."""

import html
import json
import logging
import threading
import urllib.parse
from collections.abc import Callable, Iterator
from functools import partial
from typing import Any

import django.utils.timezone
from django.conf import settings
from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse, StreamingHttpResponse
from django.template.loader import render_to_string
from pydantic import Field

from lexiflux.api import ViewGetParamsModel, get_params
from lexiflux.auth import smart_login_required
from lexiflux.custom_user import get_custom_user
from lexiflux.language.llm import (
    POOL_UNAVAILABLE_ERRORS,
    ArticleError,
    ArticleRequest,
    InlineTranslationRequest,
    ask_inline_translation,
    generate_article,
    stream_article,
)
from lexiflux.language.term_context import (
    TermContext,
    sentences_word_ids,
    term_context,
    words_span,
)
from lexiflux.language.translation import (
    AVAILABLE_TRANSLATORS,
    LLM_TRANSLATOR,
    HtmlTranslation,
    Term,
    TranslatorError,
    get_translator,
)
from lexiflux.language.wiktionary import serbian_latin
from lexiflux.language_preferences_default import LINGEA_LANGUAGES
from lexiflux.models import Book, BookPage, CustomUser, LanguagePreferences, TranslationHistory

logger = logging.getLogger(__name__)

HISTORY_CONTEXT_WORDS = 10
NDJSON_CONTENT_TYPE = "application/x-ndjson"


class TranslateGetParams(ViewGetParamsModel):
    """GET params for the /translate."""

    word_ids: str | None = Field(default=None)
    book_code: str = Field(..., min_length=1)
    book_page_number: int = Field(..., ge=1)
    lexical_article: str = Field(
        ...,
        description="Lexical article index. '0' for inline, "
        "otherwise number of the panel in Sidebar",
    )


def _generic_error_text(exc: Exception) -> str:
    # The exception text may carry secrets or internals; the traceback goes to the log instead.
    return f"An error occurred ({type(exc).__name__}). Please retry later."


def _languages_error(book_page: BookPage, language_preferences: LanguagePreferences) -> str | None:
    if not book_page.book.language:
        return "Error: Book language is not set"
    if not language_preferences.user_language:
        return "Error: User language is not set"
    return None


def _site_link(
    article_params: dict[str, Any],
    context: TermContext,
    book_page: BookPage,
    language_preferences: LanguagePreferences,
) -> dict[str, Any]:
    url = article_params.get("url", "")
    user_language = language_preferences.user_language
    lingea_language = LINGEA_LANGUAGES.get(user_language.google_code)
    if lingea_language is None and "{toLangLingea}" in url:
        return {"article": f"Lingea has no {user_language.name}–Serbian dictionary", "error": True}
    return {
        "url": url.format(
            term=urllib.parse.quote(context.word),
            termLatin=urllib.parse.quote(serbian_latin(context.word)),
            lang=book_page.book.language.name.lower(),
            langCode=book_page.book.language.google_code,
            toLang=user_language.name.lower(),
            toLangCode=user_language.google_code,
            toLangLingea=lingea_language,
        ),
        "window": article_params.get("window", True),
    }


def _dictionary_article(
    article_params: dict[str, Any],
    context: TermContext,
    book_page: BookPage,
    language_preferences: LanguagePreferences,
    user: CustomUser,
) -> str | HtmlTranslation:
    translator = get_translator(
        article_params["dictionary"],
        book_page.book.language.name,
        language_preferences.user_language.name,
    )
    result = translator.translate(Term(context.word, context.passage, user))
    if isinstance(result, HtmlTranslation):
        return result
    if not isinstance(result, str) or not result.strip():
        raise TranslatorError(TranslatorError.NOT_FOUND)
    return result


def _dictionary_error(exc: Exception, translator_name: str) -> tuple[str, str]:
    if isinstance(exc, ArticleError):
        return exc.kind, exc.html
    kind = exc.kind if isinstance(exc, TranslatorError) else ArticleError.GENERIC
    label = AVAILABLE_TRANSLATORS.get(translator_name, (None, translator_name or "Translator"))[1]
    if isinstance(exc, TranslatorError) and exc.service:
        label = exc.service
    html_text = render_to_string(
        "translator-error.html",
        {"kind": kind, "label": label, "error_type": type(exc).__name__},
    ).strip()
    return kind, html_text


def _safe_dictionary_article(
    article_params: dict[str, Any],
    context: TermContext,
    book_page: BookPage,
    language_preferences: LanguagePreferences,
    user: CustomUser,
) -> dict[str, Any]:
    try:
        article = _dictionary_article(
            article_params,
            context,
            book_page,
            language_preferences,
            user,
        )
    except Exception as e:  # noqa: BLE001
        if isinstance(e, TranslatorError):
            logger.warning("Dictionary article failed: %s", e)
        elif not isinstance(e, ArticleError):  # llm_error has logged an ArticleError
            logger.exception("Dictionary article failed")
        kind, html_text = _dictionary_error(e, article_params.get("dictionary", ""))
        return {"article": html_text, "error": True, "kind": kind}
    if isinstance(article, HtmlTranslation):
        return {"article": str(article.html), "html": True, "translation": article.translation}
    # Lines below the first are dictionary alternatives, not the translation to remember.
    return {"article": article, "translation": article.strip().split("\n", 1)[0]}


def get_lexical_article(  # noqa: PLR0913
    article_name: str,
    article_params: dict[str, Any],
    context: TermContext,
    book_page: BookPage,
    language_preferences: LanguagePreferences,
    user: CustomUser,
) -> dict[str, Any]:
    """Get the lexical article.

    Return {"article": str, "error": bool} dictionary.
    """
    if error := _languages_error(book_page, language_preferences):
        return {"article": error, "error": True}

    if article_name == "Site":
        return _site_link(article_params, context, book_page, language_preferences)

    if article_name == "Dictionary":
        return _safe_dictionary_article(
            article_params,
            context,
            book_page,
            language_preferences,
            user,
        )

    try:
        article = generate_article(
            article_request(
                article_name,
                article_params,
                context,
                book_page.book.language.name,
                language_preferences.user_language.name,
                user,
            ),
        )
        return {"article": article}
    except ArticleError as e:
        return {"article": e.html, "error": True}
    except Exception as e:  # noqa: BLE001
        logger.exception("Lexical article failed")
        return {"article": _generic_error_text(e), "error": True}


def article_request(  # noqa: PLR0913
    article_type: str,
    article_params: dict[str, Any],
    context: TermContext,
    text_language: str,
    user_language: str,
    user: CustomUser,
) -> ArticleRequest:
    return ArticleRequest(
        article_type=article_type,
        model=article_params.get("model", ""),
        effort=article_params.get("effort") or None,
        tier=article_params.get("tier") or None,
        prompt=article_params.get("prompt"),
        word=context.word,
        sentence=context.sentence,
        text_language=text_language,
        user_language=user_language,
        user=user,
    )


@smart_login_required
@get_params(TranslateGetParams)
def translate(request: HttpRequest, params: TranslateGetParams) -> HttpResponse:
    if params.lexical_article != "0":
        return JsonResponse(
            {"error": "Sidebar articles are served by /translate/stream"},
            status=400,
        )
    user = get_custom_user(request)
    book = Book.get_if_can_be_read(user, code=params.book_code)
    book_page = BookPage.objects.get(book=book, number=params.book_page_number)

    language_preferences = LanguagePreferences.get_or_create_language_preferences(
        user,
        book.language,  # type: ignore[arg-type]
    )

    assert params.word_ids is not None
    term_word_ids = [int(_id) for _id in params.word_ids.split(".")]
    context = term_context(book_page, term_word_ids)
    term_text = context.word
    logger.info(f"Selected text: {term_text}")

    if term_text.strip() == "":
        return JsonResponse({"error": "Selected text is empty"}, status=400)

    result = get_lexical_article(
        language_preferences.inline_translation_type,
        language_preferences.inline_translation_parameters,
        context,
        book_page,
        language_preferences,
        user,
    )
    if result.get("error"):
        return JsonResponse(result)

    result["article"] = result["article"].split("<hr>")[0]
    translator = _inline_translator(language_preferences)
    history_context = get_context_for_translation_history(book_page, term_word_ids)
    history = _remember(
        term_text,
        result.pop("translation", result["article"]),
        translator,
        history_context,
        book,
        language_preferences,
        user,
    )
    if _is_dictionary(translator) and not _translated_in(history, history_context):
        in_background(
            partial(
                _history_from_llm,
                history.pk,
                history.last_lookup,
                InlineTranslationRequest(
                    word=context.word,
                    passage=context.passage,
                    text_language=book.language.name,
                    user_language=language_preferences.user_language.name,
                    user=user,
                ),
                history_context,
                book.pk,
            ),
        )
    return JsonResponse(result)


def _inline_translator(language_preferences: LanguagePreferences) -> str | None:
    if language_preferences.inline_translation_type != "Dictionary":
        return None
    return language_preferences.inline_translation_parameters.get("dictionary")


def _is_dictionary(translator: str | None) -> bool:
    return translator in AVAILABLE_TRANSLATORS and translator != LLM_TRANSLATOR


def _translated_in(history: TranslationHistory, history_context: str) -> bool:
    return history.translation_from_llm and history.context == history_context


def _remember(  # noqa: PLR0913
    term_text: str,
    translation: str,
    translator: str | None,
    history_context: str,
    book: Book,
    language_preferences: LanguagePreferences,
    user: CustomUser,
) -> TranslationHistory:
    from_llm = translator == LLM_TRANSLATOR
    history, created = TranslationHistory.objects.get_or_create(
        term=term_text,
        source_language=book.language,
        user=user,
        defaults={
            "translation": translation,
            "translation_from_llm": from_llm,
            "target_language": language_preferences.user_language,
            "context": history_context,
            "book": book,
        },
    )
    if created:
        return history
    keeps_llm_translation = (
        _is_dictionary(translator)
        and history.translation_from_llm
        and history.target_language_id == language_preferences.user_language_id
    )
    # A kept LLM translation stays with its passage; the new passage comes with the new answer.
    if not keeps_llm_translation:
        history.translation = translation
        history.translation_from_llm = from_llm
        history.target_language = language_preferences.user_language
        history.context = history_context
        history.book = book
    history.lookup_count += 1
    history.last_lookup = django.utils.timezone.now()
    history.save()
    return history


def _history_from_llm(
    history_id: int,
    last_lookup: Any,
    request: InlineTranslationRequest,
    history_context: str,
    book_id: int,
) -> None:
    try:
        answer = ask_inline_translation(request)
    except POOL_UNAVAILABLE_ERRORS as e:
        logger.warning("History translation of %r failed: %r", request.word, e)
        return  # the next lookup of the word asks again
    except Exception:
        logger.exception("History translation of %r failed", request.word)
        return
    if answer:
        # A later lookup of the word, in another passage, has its own translation coming.
        TranslationHistory.objects.filter(pk=history_id, last_lookup=last_lookup).update(
            translation=answer.split("\n", 1)[0],
            translation_from_llm=True,
            context=history_context,
            book_id=book_id,
        )


def _closing_connection(work: Callable[[], None]) -> None:
    try:
        work()
    except Exception:
        logger.exception("Background work failed")
    finally:
        # A thread's database connection is its own and would otherwise stay open.
        connection.close()


def in_background(work: Callable[[], None]) -> None:
    if not settings.HISTORY_TRANSLATION_IN_BACKGROUND:
        work()
        return
    threading.Thread(
        target=_closing_connection,
        args=(work,),
        name="history-translation",
        daemon=True,
    ).start()


def _ndjson_line(event: dict[str, Any]) -> bytes:
    return (json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8")


def _error_event(message: str) -> dict[str, str]:
    return {
        "event": "error",
        "kind": ArticleError.GENERIC,
        "html": f'<div class="alert alert-danger" role="alert">{html.escape(message)}</div>',
    }


def _article_events(  # noqa: PLR0913
    article_type: str,
    article_params: dict[str, Any],
    context: TermContext,
    book_page: BookPage,
    language_preferences: LanguagePreferences,
    user: CustomUser,
) -> Iterator[dict[str, Any]]:
    if error := _languages_error(book_page, language_preferences):
        yield _error_event(error)
    elif article_type == "Site":
        link = _site_link(article_params, context, book_page, language_preferences)
        yield _error_event(link["article"]) if link.get("error") else {"event": "site", **link}
    elif article_type == "Dictionary":
        result = _safe_dictionary_article(
            article_params,
            context,
            book_page,
            language_preferences,
            user,
        )
        if result.get("error"):
            yield {"event": "error", "kind": result["kind"], "html": result["article"]}
        elif result.get("html"):
            yield {"event": "delta", "text": result["article"]}
        else:
            yield {"event": "delta", "text": html.escape(result["article"]).replace("\n", "<br>")}
    else:
        req = article_request(
            article_type,
            article_params,
            context,
            book_page.book.language.name,
            language_preferences.user_language.name,
            user,
        )
        for event in stream_article(req):
            yield event.to_dict()
    yield {"event": "done"}


@smart_login_required
@get_params(TranslateGetParams)
def translate_stream(request: HttpRequest, params: TranslateGetParams) -> HttpResponse:
    user = get_custom_user(request)
    book = Book.get_if_can_be_read(user, code=params.book_code)
    book_page = BookPage.objects.get(book=book, number=params.book_page_number)
    language_preferences = LanguagePreferences.get_or_create_language_preferences(
        user,
        book.language,  # type: ignore[arg-type]
    )

    assert params.word_ids is not None
    context = term_context(book_page, [int(_id) for _id in params.word_ids.split(".")])
    if context.word.strip() == "":
        return JsonResponse({"error": "Selected text is empty"}, status=400)

    all_articles = list(language_preferences.get_lexical_articles())
    article_index = int(params.lexical_article) - 1
    if not 0 <= article_index < len(all_articles):
        return JsonResponse({"error": "Lexical article not found"}, status=404)
    article = all_articles[article_index]

    events = _article_events(
        article.type,
        article.parameters,
        context,
        book_page,
        language_preferences,
        user,
    )
    response = StreamingHttpResponse(
        (_ndjson_line(event) for event in events),
        content_type=NDJSON_CONTENT_TYPE,
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


def get_context_for_translation_history(book_page: BookPage, term_word_ids: list[int]) -> str:
    text = book_page.content
    mapping = book_page.word_sentence_mapping
    last_word = len(book_page.words) - 1
    context = term_context(book_page, term_word_ids)

    context_start, context_end = words_span(
        book_page,
        sentences_word_ids(
            book_page,
            mapping[max(0, term_word_ids[0] - HISTORY_CONTEXT_WORDS)],
            mapping[min(last_word, term_word_ids[-1] + HISTORY_CONTEXT_WORDS)],
        ),
    )
    sentence_start, sentence_end = context.sentence_span
    term_start, term_end = context.term_span
    mark = TranslationHistory.CONTEXT_MARK
    return (
        f"{text[context_start:sentence_start]}{mark}"
        f"{text[sentence_start:term_start]}{mark}"
        f"{text[term_end:sentence_end]}{mark}"
        f"{text[sentence_end:context_end]}"
    )
