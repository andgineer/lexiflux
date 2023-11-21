"""Vies for the Lexiflux app."""
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string

from .models import BookPage


def book(request: HttpRequest) -> HttpResponse:
    """Fetch paginated book and render only visible pages."""
    page_number = request.GET.get("book-page", 1)
    page = BookPage.objects.get(number=page_number)
    # todo: get two pages for prev and next
    return render(request, "book.html", {"page": page})


def book_page(request: HttpRequest) -> HttpResponse:
    """Render the book page."""
    page_number = request.GET.get("book-page", 1)
    try:
        next_page = BookPage.objects.get(number=page_number)
    except BookPage.DoesNotExist:
        return HttpResponse(f"error: Page {page_number} not found", status=500)

    # Render only the content of the next page as a partial HTML response
    content = render_to_string("page.html", {
        "page": next_page,
        "type": request.GET.get("type"),
        "book_page": request.GET.get("book-page"),
    })

    return HttpResponse(content)
