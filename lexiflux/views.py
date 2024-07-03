"""Vies for the Lexiflux app."""

import json
from typing import Optional, Dict, Any
import urllib.parse

from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import models
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods
from pydantic import Field

from core.models import CustomUser
from lexiflux.language.translation import get_translator
from lexiflux.api import get_params, ViewGetParamsModel

from lexiflux.models import Book, BookPage, ReadingHistory, ReadingLoc, LexicalArticle, Language


def render_page(page_db: BookPage) -> str:
    """Render the page using the parsed word."""
    content = page_db.content
    result = []
    last_end = 0

    for word_idx, word_pos in enumerate(page_db.words):
        # Add text between words (if any)
        start, end = word_pos
        if start > last_end:
            result.append(content[last_end:start])

        # Add the word with span
        word = content[start:end]
        result.append(f'<span id="word-{word_idx}" class="word">{word}</span>')
        last_end = end

    # Add any remaining text after the last word
    if last_end < len(content):
        result.append(content[last_end:])

    return "".join(result)


def redirect_to_reader(request: HttpRequest) -> HttpResponse:
    """Redirect to the 'reader' view."""
    return redirect("reader")


def can_see_book(user: CustomUser, book: Book) -> bool:
    """Check if the user can see the book."""
    return user.is_superuser or book.owner == user or user in book.shared_with.all() or book.public


@login_required  # type: ignore
def reader(request: HttpRequest) -> HttpResponse:
    """Open the book in reader.

    If the book code not given open the latest book.
    """
    book_code = request.GET.get("book-code")
    page_number = request.GET.get("book-page-number")
    book = Book.objects.filter(code=book_code).first() if book_code else None
    if not book:
        if book_code:
            print(f"Book {book_code} not found")
        if not (reading_location := ReadingLoc.objects.filter(user=request.user).first()):
            return redirect("library")  # Redirect if the user has no reading history

        book = reading_location.book
        book_code = book.code  # Update book_code to be used in the response
        page_number = reading_location.page_number
    # Security check to ensure the user is authorized to view the book
    if not can_see_book(request.user, book):
        return HttpResponse("Forbidden", status=403)

    if not page_number:
        # if the book-code is provided but book-page-number is not: first page or last read page
        reading_location = ReadingLoc.objects.filter(book=book, user=request.user).first()
        page_number = reading_location.page_number if reading_location else 1
    else:
        page_number = int(page_number)  # Ensure page_number is an integer

    print(f"Opening book {book_code} at page {page_number} for user {request.user.username}")
    book_page = BookPage.objects.get(book=book, number=page_number)

    return render(
        request,
        "reader.html",
        {
            "book": book_page.book,
            "page": book_page,
            "top_word": 0,
        },
    )


@login_required  # type: ignore
def page(request: HttpRequest) -> HttpResponse:
    """Book page.

    In addition to book and page num should include top word id to save the location.
    """
    book_code = request.GET.get("book-code")
    page_number = request.GET.get("book-page-number")
    try:
        page_number = int(page_number)
        book_page = BookPage.objects.filter(book__code=book_code, number=page_number).first()
        if not book_page:
            raise BookPage.DoesNotExist
    except (BookPage.DoesNotExist, ValueError):
        return HttpResponse(
            f"error: Page {page_number} not found in book '{book_code}'", status=500
        )
    # check access
    if not can_see_book(request.user, book_page.book):
        return HttpResponse(status=403)

    # Update the reading location
    location(request)

    print(f"Rendering page {page_number} of book {book_code}")
    page_html = render_page(book_page)

    return JsonResponse(
        {
            "html": page_html,
            "data": {
                "bookCode": book_code,
                "pageNumber": page_number,
            },
        }
    )


@login_required  # type: ignore
def location(request: HttpRequest) -> HttpResponse:
    """Read location changed."""
    try:
        book_code = request.GET.get("book-code")
        page_number = int(request.GET.get("book-page-number"))
        top_word = int(request.GET.get("top-word", 0))
        if not book_code:
            raise ValueError("book-code is missing")
    except (TypeError, ValueError, KeyError):
        return HttpResponse("Invalid or missing parameters", status=400)

    book = Book.objects.get(code=book_code)
    if not can_see_book(request.user, book):
        return HttpResponse(status=403)  # Forbidden

    ReadingLoc.update_reading_location(
        user=request.user, book_id=book.id, page_number=page_number, top_word_id=top_word
    )
    return HttpResponse(status=200)


class TranslateGetParams(ViewGetParamsModel):
    """GET params for the /translate."""

    text: str = Field(..., min_length=1)
    book_code: str = Field(..., min_length=1)
    translate: bool = Field(default=True)
    lexical_article: Optional[str] = Field(default=None)


@login_required  # type: ignore
@get_params(TranslateGetParams)
def translate(request: HttpRequest, params: TranslateGetParams) -> HttpResponse:
    """Translate text.

    full: if true, side panel is visible so we prepare detailed translation materials.
    """
    user_id = request.user.id
    print("Translating text")
    # word_id = request.GET.get("word-id")  # todo: absolute word ID so we can find context

    # lexical_articles = LexicalArticles()
    translated = ""
    if params.translate:
        print("Translating", params.text)
        translator = get_translator(params.book_code, user_id)
        print("Translator", translator)
        translated = translator.translate(params.text)
        print("Translated", translated)
        # todo: get article from the translator

    result: Dict[str, Any] = {"translatedText": translated}
    articles = {}
    if params.lexical_article:
        print("Fetching lexical article")
        # articles_map = {
        #     1: "Dictionary",
        #     "Dictionary Advanced": "Dictionary\u2601$+",
        #     2: "Examples",
        #     3: "Explain",
        # }
        # todo: get context as text and the selection as word
        # articles[params.lexical_article] = lexical_articles.get_article(
        #     articles_map[params.lexical_article],
        #     params.text,
        #     "",
        #     "sr",
        #     "ru",
        # )
        # f"""<p>{params.text} {params.lexical_article}</p>"""
        articles[params.lexical_article] = f"{params.text} {params.lexical_article}"
        result["articles"] = articles
        if params.lexical_article == "3":
            result["url"] = f"https://glosbe.com/sr/ru/{urllib.parse.quote(params.text)}"
            result["window"] = True
    return JsonResponse(result)


@login_required  # type: ignore
def profile(request: HttpRequest) -> HttpResponse:
    """Profile page."""
    reader_profile = request.user.reader_profile
    return render(
        request,
        "profile.html",
        {
            "user": request.user,
            "reader_profile": reader_profile,
        },
    )


@login_required  # type: ignore
@require_http_methods(["POST"])  # type: ignore
def manage_lexical_article(request: HttpRequest) -> JsonResponse:  # pylint: disable=too-many-return-statements
    """Add, edit, or delete a lexical article."""
    data = json.loads(request.body)
    action = data.get("action")
    reader_profile = request.user.reader_profile

    if action == "add":
        # Check for duplicate titles
        if LexicalArticle.objects.filter(
            reader_profile=reader_profile, title=data["title"]
        ).exists():
            return JsonResponse(
                {"status": "error", "message": "An article with this title already exists"}
            )

        article = LexicalArticle.objects.create(
            reader_profile=reader_profile,
            type=data["type"],
            title=data["title"],
            parameters=data["parameters"],
        )
        return JsonResponse({"status": "success", "id": article.id})

    if action == "edit":
        try:
            article = LexicalArticle.objects.get(id=data["id"], reader_profile=reader_profile)
            # Check for duplicate titles, excluding the current article
            if (
                LexicalArticle.objects.filter(reader_profile=reader_profile, title=data["title"])
                .exclude(id=data["id"])
                .exists()
            ):
                return JsonResponse(
                    {"status": "error", "message": "An article with this title already exists"}
                )

            article.type = data["type"]
            article.title = data["title"]
            article.parameters = data["parameters"]
            article.save()
            return JsonResponse({"status": "success"})
        except LexicalArticle.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Article not found"})

    elif action == "delete":
        LexicalArticle.objects.filter(id=data["id"], reader_profile=reader_profile).delete()
        return JsonResponse({"status": "success"})

    return JsonResponse({"status": "error", "message": "Invalid action"})


@login_required  # type: ignore
@require_http_methods(["POST"])  # type: ignore
def save_inline_translation(request: HttpRequest) -> JsonResponse:
    """Save the inline translation setting."""
    data = json.loads(request.body)
    inline_translation = data.get("inline_translation", "")

    reader_profile = request.user.reader_profile
    reader_profile.inline_translation = inline_translation
    reader_profile.save()

    return JsonResponse({"status": "success"})


@login_required  # type: ignore
def get_models(request: HttpRequest) -> JsonResponse:
    """Return the available models."""
    models_list = ["gpt-3.5-turbo", "gpt-4-turbo"]
    return JsonResponse({"models": models_list})


@login_required  # type: ignore
@require_http_methods(["POST"])  # type: ignore
def update_profile(request: HttpRequest) -> JsonResponse:
    """Update the user profile."""
    data = json.loads(request.body)
    field = data.get("field")
    value = data.get("value")

    reader_profile = request.user.reader_profile

    if field == "email":
        request.user.email = value
        request.user.save()
    elif field == "nativeLanguage":
        language, _ = Language.objects.get_or_create(name=value)
        reader_profile.native_language = language
    elif field == "currentBook":
        book = Book.objects.filter(title=value).first()
        reader_profile.current_book = book
    else:
        return JsonResponse({"status": "error", "message": "Invalid field"})

    reader_profile.save()
    return JsonResponse({"status": "success"})


@login_required  # type: ignore
def library(request: HttpRequest) -> HttpResponse:
    """Library page."""
    if request.user.is_superuser:
        # If the user is a superuser, show all books
        books_query = Book.objects.all()
    else:
        # Filter books for regular users
        books_query = Book.objects.filter(
            models.Q(owner=request.user)
            | models.Q(shared_with=request.user)
            | models.Q(public=True)
        )

    books_query = (
        books_query.annotate(
            updated=models.Max(
                "readingloc__updated", filter=models.Q(readingloc__user=request.user)
            )
        )
        .order_by("-updated", "title")
        .distinct()
    )

    # Pagination
    page_number = request.GET.get("page")
    paginator = Paginator(books_query, 10)  # Show 10 books per page

    try:
        books = paginator.page(page_number)
    except PageNotAnInteger:
        books = paginator.page(1)  # Default to the first page
    except EmptyPage:
        books = paginator.page(
            paginator.num_pages
        )  # Go to the last page if the page is out of range

    return render(request, "library.html", {"books": books})


@login_required  # type: ignore
@require_POST  # type: ignore
def add_to_history(request: HttpRequest) -> JsonResponse:
    """Add the location to History."""
    user = request.user

    book_id = request.POST.get("book_id")
    page_number = request.POST.get("page_number")
    top_word_id = request.POST.get("top_word_id")

    try:
        book_id = int(book_id)
        page_number = int(page_number)
        top_word_id = int(top_word_id)
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid input"}, status=400)

    book = get_object_or_404(Book, id=book_id)
    if not can_see_book(request.user, book):
        return HttpResponse(status=403)  # Forbidden

    ReadingHistory.objects.create(
        user=user,
        book=book,
        page_number=page_number,
        top_word_id=top_word_id,
        read_time=timezone.now(),
    )

    return JsonResponse({"message": "Reading history added successfully"})


@login_required  # type: ignore
def view_book(request: HttpRequest) -> HttpResponse:
    """Book detail page."""
    book_code = request.GET.get("book-code")
    book = get_object_or_404(Book, code=book_code)

    if not can_see_book(request.user, book):
        return HttpResponse(status=403)  # Forbidden

    context = {
        "book": book,
    }

    return render(request, "book.html", context)
