"""Library partial views."""

import logging
from typing import Type, Dict, Any, Optional

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import TemporaryUploadedFile
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q
from django.http import HttpResponse, HttpRequest, JsonResponse
from django.shortcuts import render
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import TemplateView
from django.db import models

from lexiflux.ebook.book_loader_base import BookLoaderBase
from lexiflux.ebook.book_loader_epub import BookLoaderEpub
from lexiflux.ebook.book_loader_html import BookLoaderHtml
from lexiflux.ebook.book_loader_plain_text import BookLoaderPlainText
from lexiflux.models import Book, Language, Author
from lexiflux.decorators import smart_login_required


logger = logging.getLogger(__name__)

AUTHOR_SUGGESTION_PAGE_SIZE = 15


@smart_login_required
@require_GET  # type: ignore
def books_list(request: HttpRequest) -> HttpResponse:
    """Return the paginated books list partial."""
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
                "readingloc__last_access", filter=models.Q(readingloc__user=request.user)
            )
        )
        .order_by("-updated", "title")
        .select_related("author")
        .distinct()
    )

    # Pagination
    page_number = request.GET.get("page")
    paginator = Paginator(books_query, 10)  # Show 10 books per page

    try:
        books_page = paginator.page(page_number)
    except PageNotAnInteger:
        books_page = paginator.page(1)  # Default to the first page
    except EmptyPage:
        books_page = paginator.page(
            paginator.num_pages
        )  # Go to the last page if the page is out of range

    # Format last_read for each book
    for book in books_page:
        book.formatted_last_read = book.format_last_read(request.user)
        book.last_position_percent = book.reading_loc(request.user).last_position_percent

    return render(request, "partials/books_list.html", {"books": books_page})


@method_decorator(smart_login_required, name="dispatch")
class EditBookModalPartial(TemplateView):  # type: ignore
    """Edit book modal partial view."""

    template_name = "partials/book_modal.html"
    book: Optional[Book] = None

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Handle all HTTP methods with proper error checking."""
        try:
            self.book = Book.get_if_can_be_read(request.user, id=kwargs.get("book_id"))
            return super().dispatch(request, *args, **kwargs)
        except (ObjectDoesNotExist, PermissionDenied, ValueError) as e:
            # The middleware will handle converting this to the appropriate JSON response
            raise e
        except Exception as e:
            logger.error("Error accessing book: %s", e, exc_info=True)
            raise ValueError("An error occurred while processing your request") from e

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """Get context data for the template."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "book": self.book,
                "is_new": self.request.GET.get("is_new", False),
                "languages": Language.objects.all(),
            }
        )
        return context  # type: ignore

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Update book details."""
        try:
            # Validate required fields
            title = request.POST.get("title")
            author_name = request.POST.get("author")
            language_code = request.POST.get("language")

            if not title:
                raise ValueError("Title is required")
            if not author_name:
                raise ValueError("Author is required")
            if not language_code:
                raise ValueError("Language is required")

            # Update book details
            assert self.book is not None
            self.book.title = title
            author, _ = Author.objects.get_or_create(name=author_name)
            self.book.author = author
            language = Language.objects.get(google_code=language_code)
            self.book.language = language
            self.book.save()

            return HttpResponse()

        except ValueError as e:
            return TemplateResponse(
                request,
                self.template_name,
                {**self.get_context_data(**kwargs), "error_message": str(e)},
            )
        except Exception as e:
            logger.error("Error updating book: %s", e, exc_info=True)
            raise ValueError(f"An error occurred while saving the book: {e}") from e

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        """Delete a book."""
        try:
            assert self.book is not None
            if self.book.owner and (
                self.book.owner != request.user and not request.user.is_superuser
            ):
                raise PermissionDenied("You don't have permission to delete this book")
            self.book.delete()
            return JsonResponse({"success": "Book deleted successfully"})
        except Exception as e:
            logger.error("Error deleting book: %s", e, exc_info=True)
            raise ValueError("An error occurred while deleting the book") from e


@smart_login_required
@require_GET  # type: ignore
def import_modal(request: HttpRequest) -> HttpResponse:
    """Return the import modal partial."""
    return render(request, "partials/import_modal.html")


@smart_login_required
@require_POST  # type: ignore
def import_book(request: HttpRequest) -> HttpResponse:
    """Handle book import and return appropriate modal."""
    try:
        file = request.FILES.get("file")
        if not file:
            raise ValueError("No file provided")

        original_filename = file.name
        file_extension = original_filename.split(".")[-1].lower()

        book_class: Type[BookLoaderBase]
        if file_extension == "txt":
            book_class = BookLoaderPlainText
        elif file_extension == "html":
            book_class = BookLoaderHtml
        elif file_extension == "epub":
            book_class = BookLoaderEpub
        else:
            raise ValueError(f"Unsupported file format for {file.name}")

        if isinstance(file, TemporaryUploadedFile):
            book_processor = book_class(
                file.temporary_file_path(), original_filename=original_filename
            )
            book = book_processor.create(request.user.email)
            book.save()
        else:
            # For in-memory files, save to disk
            fs = FileSystemStorage(location="/tmp")
            filename = fs.save(original_filename, file)
            try:
                book_processor = book_class(fs.path(filename), original_filename=original_filename)
                book = book_processor.create(request.user.email)
                book.save()
            finally:
                fs.delete(filename)

        context = {
            "book": book,
            "languages": Language.objects.all(),
            "is_new": True,
        }
        return HttpResponse(f"""
            <script>
                document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
                htmx.trigger('body', 'show-edit-modal');
            </script>
            {render(request, "partials/book_modal.html", context).content.decode('utf-8')}
        """)

    except Exception as e:  # pylint: disable=broad-except
        logging.error("Error importing book: %s", e, exc_info=True)
        return render(
            request,
            "partials/import_modal.html",
            {
                "error_message": str(e),
                "last_filename": request.FILES.get("file").name
                if request.FILES.get("file")
                else None,
            },
        )


@smart_login_required  # type: ignore
def search_authors(request: HttpRequest) -> HttpResponse:
    """Search authors based on input string in `author`."""
    query = request.GET.get("author", "").strip()

    # Always render the template, just with empty authors list if no query
    if not query:
        return render(
            request, "partials/author_suggestions.html", {"authors": [], "has_more": False}
        )

    # Rest of the function remains the same...
    if " " in query:
        authors = Author.objects.filter(name__icontains=query)[: AUTHOR_SUGGESTION_PAGE_SIZE + 1]
    else:
        authors = Author.objects.filter(
            Q(name__istartswith=query)  # Starts with the query
            | Q(name__icontains=f" {query}")  # Space before query
            | Q(name__icontains=f"-{query}")  # Hyphen before query
            | Q(name__icontains=f".{query}")  # Period before query
        )[: AUTHOR_SUGGESTION_PAGE_SIZE + 1]

    has_more = len(authors) > AUTHOR_SUGGESTION_PAGE_SIZE
    authors = authors[:AUTHOR_SUGGESTION_PAGE_SIZE]  # Trim if there are more

    return render(
        request, "partials/author_suggestions.html", {"authors": authors, "has_more": has_more}
    )


@smart_login_required
@require_GET  # type: ignore
def library_page(request: HttpRequest) -> HttpResponse:
    """Render the main library page."""
    return render(request, "library.html")
