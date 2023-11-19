"""Vies for the Lexiflux app."""
from django.core.paginator import Paginator
from django.shortcuts import render
from django.http import JsonResponse
from django.template.loader import render_to_string

from .models import BookPage


def book(request):
    """Fetch paginated book and render only visible pages."""
    page_number = request.GET.get("page", 1)
    page = BookPage.objects.get(number=page_number)

    return render(request, "book.html", {"page": page})


def book_page(request):
    """Render the book page."""
    page_number = request.GET.get("page", 1)
    try:
        next_page = BookPage.objects.get(number=page_number)
    except BookPage.DoesNotExist:
        return JsonResponse({"error": "Page not found"})

    # Render only the content of the next page as a partial HTML response
    content = render_to_string("page.html", {"page": next_page})

    return JsonResponse({"content": content})