"""Vies for the Lexiflux app."""
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string

from .models import BookPage


def book(request: HttpRequest) -> HttpResponse:
    """Fetch paginated book and render only visible pages."""
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
        "book.html",
        {
            "page": page,
            "words": words,
        },
    )

    return HttpResponse(content)
