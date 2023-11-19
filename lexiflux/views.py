"""Vies for the LexiFlux app."""
from django.core.paginator import Paginator
from django.shortcuts import render

from .models import BookPage


def book(request):
    """Fetch paginated book and render only visible pages."""
    page_number = request.GET.get("page", 1)
    paginator = Paginator(BookPage.objects.all(), 2)  # pylint: disable=no-member
    pages = paginator.get_page(page_number)

    return render(request, "book.html", {"pages": pages})
