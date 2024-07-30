"""Views for the library and Book pages."""

import json
import traceback
from typing import Type

from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import TemporaryUploadedFile
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db import models
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth.decorators import login_required
from django.db.models import Q

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

    # Get languages for the dropdown
    languages = list(Language.objects.values("google_code", "name"))

    context = {
        "books": books,
        "languages": json.dumps(languages),
    }
    return render(request, "library.html", context)


# todo: obsolete
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
            if isinstance(file, TemporaryUploadedFile):
                book_processor = book_class(file.temporary_file_path())
                book = book_base.import_book(book_processor, request.user.email)
            else:
                # For in-memory files, save to disk
                fs = FileSystemStorage(location="/tmp")
                filename = fs.save(file.name, file)
                try:
                    book_processor = book_class(fs.path(filename))
                    book = book_base.import_book(book_processor, request.user.email)
                finally:
                    fs.delete(filename)

            return JsonResponse(
                {
                    "id": book.id,
                    "title": book.title,
                    "author": book.author.name,
                    "language": book.language.google_code,
                }
            )
        except Exception as e:  # pylint: disable=broad-except
            print(e)
            traceback_str = traceback.format_exc()
            print(traceback_str)
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)


@method_decorator(login_required, name="dispatch")
class BookDetailView(View):  # type: ignore
    """View for book details."""

    def get(self, request: HttpRequest, book_id: int) -> JsonResponse:
        """Get book details."""
        try:
            book = Book.objects.get(id=book_id)
            return JsonResponse(
                {
                    "id": book.id,
                    "title": book.title,
                    "author": book.author.name,
                    "language": book.language.google_code,
                }
            )
        except Book.DoesNotExist:
            return JsonResponse({"error": "Book not found"}, status=404)

    def put(self, request: HttpRequest, book_id: int) -> JsonResponse:
        """Update book details."""
        try:
            book = Book.objects.get(id=book_id)
            data = json.loads(request.body)

            book.title = data.get("title", book.title)

            author_name = data.get("author", book.author.name)
            author, _ = Author.objects.get_or_create(name=author_name)
            book.author = author

            language = Language.objects.get(
                google_code=data.get("language", book.language.google_code)
            )
            book.language = language

            book.save()

            return JsonResponse(
                {
                    "id": book.id,
                    "title": book.title,
                    "author": book.author.name,
                    "language": book.language.google_code,
                }
            )
        except Book.DoesNotExist:
            return JsonResponse({"error": "Book not found"}, status=404)
        except Exception as e:  # pylint: disable=broad-except
            return JsonResponse({"error": str(e)}, status=500)

        return JsonResponse({"error": "Invalid request method"}, status=405)


@login_required  # type: ignore
def search_authors(request: HttpRequest) -> JsonResponse:
    """Search authors based on input string."""
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"authors": [], "has_more": False})

    # If the query contains spaces (more than one word), search for the entire string
    if " " in query:
        authors = Author.objects.filter(name__icontains=query)[:101]
    else:
        # For single words, search for the word at the start of any word in the name
        # including words separated by hyphens and periods
        authors = Author.objects.filter(
            Q(name__istartswith=query)  # Starts with the query
            | Q(name__icontains=f" {query}")  # Space before query
            | Q(name__icontains=f"-{query}")  # Hyphen before query
            | Q(name__icontains=f".{query}")  # Period before query
        )[:101]

    has_more = len(authors) > 100
    authors = authors[:100]  # Trim to 100 if there are more

    return JsonResponse({"authors": [author.name for author in authors], "has_more": has_more})
