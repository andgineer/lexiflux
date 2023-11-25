"""Vies for the Lexiflux app."""
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template import Context, Template
from django.template.loader import render_to_string

from .models import BookPage


def book(request: HttpRequest) -> HttpResponse:
    """Render book."""
    book_id = request.GET.get("book-id", 1)
    page_number = request.GET.get("page-num", 1)
    page = BookPage.objects.get(book_id=book_id, number=page_number)
    words = page.content.split(" ")
    return render(
        request,
        "book.html",
        {
            "book": page.book,
            "page": page,
            "words": words,
        },
    )


def book_page(request: HttpRequest) -> HttpResponse:
    """Render the book page."""
    book_id = request.GET.get("book-id", 1)
    page_number = request.GET.get("page-num", 1)
    try:
        page = BookPage.objects.get(book_id=book_id, number=page_number)
    except BookPage.DoesNotExist:
        return HttpResponse(f"error: Page {page_number} not found", status=500)
    last_word_id = request.GET.get("last-word-id", "0")
    last_word_id = int(last_word_id) if last_word_id.isdigit() else 0
    print(book_id, page_number, "last_word_id", last_word_id)
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
    book_id = request.GET.get("book-id", 1)
    page_number = request.GET.get("page-num", 1)
    word_id = request.GET.get("id", 1)
    try:
        page = BookPage.objects.get(
            book_id=book_id,
            number=page_number,
        )
    except BookPage.DoesNotExist:
        return HttpResponse(f"error: Page {page_number} not found", status=500)
    words = page.content.split(" ")
    word = words[int(word_id) - 1]  # Django forloop.counter starts at 1
    print(book_id, page_number, word_id, word)
    template = Template(
        """<span id="word-{{ word_id }}" class="word"
          hx-trigger="click"
          hx-get="{% url 'word' %}?id={{ word_id }}"
          hx-swap="outerHTML">{{ word }}</span>"""
    )
    context = Context({"word": word, "word_id": word_id})
    content = template.render(context)
    return HttpResponse(content)
