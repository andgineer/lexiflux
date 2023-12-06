"""Vies for the Lexiflux app."""
from deep_translator import GoogleTranslator
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string

from .models import Book, BookPage


@login_required  # type: ignore
def book(request: HttpRequest) -> HttpResponse:
    """Render book."""
    book_id = request.GET.get("book-id", 1)
    page_number = request.GET.get("page-num", 1)
    page_number = BookPage.objects.get(book_id=book_id, number=page_number)
    return render(
        request,
        "book.html",
        {
            "book": page_number.book,
            "page": page_number,
            "top_word": 0,
        },
    )


@login_required  # type: ignore
def page(request: HttpRequest) -> HttpResponse:
    """Book page."""
    book_id = request.GET.get("book-id", 1)
    page_number = request.GET.get("page-num", 1)
    try:
        book_page = BookPage.objects.get(book_id=book_id, number=page_number)
    except BookPage.DoesNotExist:
        return HttpResponse(f"error: Page {page_number} not found", status=500)
    words = book_page.content.split(" ")
    print(book_id, page_number, "words", len(words))
    rendered_html = render_to_string(
        "page.html",
        {
            "book": book_page.book,
            "page": book_page,
            "words": words,
        },
        request,
    )

    return JsonResponse(
        {
            "html": rendered_html,
            "data": {
                "bookId": book_id,
                "pageNum": page_number,
                "words": words,
            },
        }
    )


@login_required  # type: ignore
def viewport(request: HttpRequest) -> HttpResponse:
    """User changed viewport inside loaded book page."""
    book_id = request.GET.get("book-id", 1)
    page_number = request.GET.get("page-num", 1)
    # todo: save viewport in the user session
    # try:
    #     page = BookPage.objects.get(book_id=book_id, number=page_number)
    # except BookPage.DoesNotExist:
    #     return HttpResponse(f"error: Page {page_number} not found", status=500)
    top_word = request.GET.get("top-word", 0)
    top_word = int(top_word)
    print(book_id, page_number, "top_word", top_word)
    return HttpResponse(status=200)


def translate(request: HttpRequest) -> HttpResponse:
    """Translate event."""
    text = request.GET.get("text", "")
    source = "sr"
    target = "ru"
    translated = GoogleTranslator(source=source, target=target).translate(text)
    return HttpResponse(translated)


@login_required  # type: ignore
def profile(request: HttpRequest) -> HttpResponse:
    # if not request.user.is_approved:
    """Profile page."""
    return render(request, "profile.html")


@login_required  # type: ignore
def library(request: HttpRequest) -> HttpResponse:
    """Retrieve books shared with the user or public books."""
    books = Book.objects.filter(
        models.Q(shared_with=request.user) | models.Q(visibility=Book.PUBLIC)
    ).distinct()
    return render(request, "library.html", {"books": books})
