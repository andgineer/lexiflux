"""Vies for the Lexiflux app."""
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string

from .models import BookPage


def book(request) -> HttpResponse:
    """Fetch paginated book and render only visible pages."""
    page_number = request.GET.get("page", 1)
    page = BookPage.objects.get(number=page_number)

    return render(request, "book.html", {"page": page})


def book_page(request) -> HttpResponse:
    """Render the book page."""
    page_number = request.GET.get("page", 1)
    try:
        next_page = BookPage.objects.get(number=page_number)
    except BookPage.DoesNotExist:
        return HttpResponse(f"error: Page {page_number} not found", status=500)

    # Render only the content of the next page as a partial HTML response
    content = render_to_string("page.html", {"page": next_page})

    return HttpResponse(content)
