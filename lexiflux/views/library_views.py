"""Views for the library and Book pages."""

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db import models
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, get_object_or_404

from lexiflux.models import Book
from lexiflux.views.reader_views import can_see_book


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
