"""Views for the library and Book pages."""

import json
from typing import Type

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db import models
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from lexiflux.ebook.book_base import BookBase
from lexiflux.views.reader_views import can_see_book
from lexiflux.models import Book, Author, Language
from lexiflux.ebook.book_plain_text import BookPlainText
from lexiflux.ebook.book_html import BookHtml
from lexiflux.ebook.book_epub import BookEpub
from lexiflux.ebook import book_base


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


# rodo: obsolete
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


@csrf_exempt  # type: ignore
@login_required  # type: ignore
def import_book(request: HttpRequest) -> JsonResponse:
    """Import a book from a file."""
    if request.method == "POST":
        file = request.FILES.get("file")
        if not file:
            return JsonResponse({"error": "No file provided"}, status=400)

        book_class: Type[BookBase]
        file_extension = file.name.split(".")[-1].lower()
        if file_extension == "txt":
            book_class = BookPlainText
        elif file_extension == "html":
            book_class = BookHtml
        elif file_extension == "epub":
            book_class = BookEpub
        else:
            return JsonResponse({"error": "Unsupported file format"}, status=400)

        try:
            book_processor = book_class(file)
            book = book_base.import_book(book_processor, request.user.email)
            return JsonResponse(
                {
                    "id": book.id,
                    "title": book.title,
                    "author": book.author.name,
                    "language": book.language.name,
                }
            )
        except Exception as e:  # pylint: disable=broad-except
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)


@login_required  # type: ignore
def get_book(request: HttpRequest, book_id: str) -> JsonResponse:
    """Get book details."""
    try:
        book = Book.objects.get(id=book_id)
        return JsonResponse(
            {
                "id": book.id,
                "title": book.title,
                "author": book.author.name,
                "language": book.language.name,
            }
        )
    except Book.DoesNotExist:
        return JsonResponse({"error": "Book not found"}, status=404)


@csrf_exempt  # type: ignore
@login_required  # type: ignore
def update_book(request: HttpRequest, book_id: str) -> JsonResponse:
    """Update book details."""
    if request.method == "PUT":
        try:
            book = Book.objects.get(id=book_id)
            data = json.loads(request.body)

            book.title = data.get("title", book.title)

            author, _ = Author.objects.get_or_create(name=data.get("author", book.author.name))
            book.author = author

            language, _ = Language.objects.get_or_create(
                name=data.get("language", book.language.name)
            )
            book.language = language

            book.save()

            return JsonResponse(
                {
                    "id": book.id,
                    "title": book.title,
                    "author": book.author.name,
                    "language": book.language.name,
                }
            )
        except Book.DoesNotExist:
            return JsonResponse({"error": "Book not found"}, status=404)
        except Exception as e:  # pylint: disable=broad-except
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)
