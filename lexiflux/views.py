"""Vies for the Lexiflux app."""
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template import Context, Template
from django.template.loader import render_to_string

from .models import BookPage


def book(request: HttpRequest) -> HttpResponse:
    """Render book."""
    page_number = request.GET.get("book-page", 1)
    page = BookPage.objects.get(number=page_number)
    words = page.content.split(" ")
    return render(
        request,
        "book.html",
        {
            "page": page,
            "words": words,
        },
    )


def book_page(request: HttpRequest) -> HttpResponse:
    """Render the book page."""
    page_number = request.GET.get("book-page", 1)
    try:
        page = BookPage.objects.get(number=page_number)
    except BookPage.DoesNotExist:
        return HttpResponse(f"error: Page {page_number} not found", status=500)
    last_word_id = request.GET.get("last-word-id", "0")
    last_word_id = int(last_word_id) if last_word_id.isdigit() else 0
    print("last_word_id", last_word_id)
    words = page.content.split(" ")
    content = render_to_string(
        "page.html",
        {
            "page": page,
            "words": words,
        },
    )

    return HttpResponse(content)


def word_click(request: HttpRequest) -> HttpResponse:
    """Word click event."""
    page_number, word_number = request.GET.get("id", 1).split(":")
    try:
        page = BookPage.objects.get(number=page_number)
    except BookPage.DoesNotExist:
        return HttpResponse(f"error: Page {page_number} not found", status=500)
    words = page.content.split(" ")
    word = words[int(word_number) - 1]  # word_number is 1-based
    print("word", page_number, word_number, word)
    template = Template("<span id='word-{{ page.number }}:{{ word_id }}'>{{ word }}</span>")
    context = Context({"word": word, "word_id": word_number})
    content = template.render(context)
    return HttpResponse(content)
