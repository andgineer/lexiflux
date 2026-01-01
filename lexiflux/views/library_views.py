"""Library partial views with URL import functionality."""

import logging
from typing import Any

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import models
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView

from lexiflux.decorators import smart_login_required
from lexiflux.lexiflux_settings import settings
from lexiflux.models import Author, Book, Language

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
            | models.Q(public=True),
        )

    books_query = (
        books_query.annotate(
            updated=models.Max(
                "readingloc__last_access",
                filter=models.Q(readingloc__user=request.user),
            ),
        )
        .order_by("-updated", "title")
        .select_related("author")
        .distinct()
    )

    # Pagination
    page_number = request.GET.get("page", "1")
    paginator = Paginator(books_query, 10)  # Show 10 books per page

    try:
        books_page = paginator.page(page_number)
    except PageNotAnInteger:
        books_page = paginator.page(1)  # Default to the first page
    except EmptyPage:
        books_page = paginator.page(
            paginator.num_pages,
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
    book: Book | None = None

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Handle all HTTP methods with proper error checking."""
        try:
            self.book = Book.get_if_can_be_read(request.user, id=kwargs.get("book_id"))
            return super().dispatch(request, *args, **kwargs)
        except (ObjectDoesNotExist, PermissionDenied, ValueError):
            # The middleware will handle converting this to the appropriate JSON response
            raise
        except Exception as e:
            logger.exception("Error accessing book")
            raise ValueError("An error occurred while processing your request") from e

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Get context data for the template."""
        context = super().get_context_data(**kwargs)
        require_delete_confirmation = (
            self.request.GET.get("require_delete_confirmation", "true").lower() != "false"
        )
        show_delete_button = self.request.GET.get("show_delete_button", "true").lower() != "false"
        context.update(
            {
                "book": self.book,
                "require_delete_confirmation": require_delete_confirmation,
                "show_delete_button": show_delete_button,
                "languages": Language.objects.all(),
                "skip_auth": settings.lexiflux.skip_auth,
            },
        )
        return context  # type: ignore

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:  # noqa: ARG002
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

            # Only update public field if not in autologin mode
            if not settings.lexiflux.skip_auth:
                self.book.public = request.POST.get("public") == "on"

            self.book.save()

            return HttpResponse()

        except ValueError as e:
            assert (  # Tells pyrefly "this is definitely not None here"
                self.template_name is not None
            )
            return TemplateResponse(
                request,
                self.template_name,
                {**self.get_context_data(**kwargs), "error_message": str(e)},
            )
        except Exception as e:
            logger.exception("Error updating book")
            raise ValueError(f"An error occurred while saving the book: {e}") from e

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:  # noqa: ARG002
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
            logger.exception("Error deleting book")
            raise ValueError("An error occurred while deleting the book") from e


@smart_login_required  # type: ignore
def search_authors(request: HttpRequest) -> HttpResponse:
    """Search authors based on input string in `author`."""
    query = request.GET.get("author", "").strip()

    # Always render the template, just with empty authors list if no query
    if not query:
        return render(
            request,
            "partials/author_suggestions.html",
            {"authors": [], "has_more": False},
        )

    # Rest of the function remains the same...
    if " " in query:
        authors = Author.objects.filter(name__icontains=query)[: AUTHOR_SUGGESTION_PAGE_SIZE + 1]
    else:
        authors = Author.objects.filter(
            Q(name__istartswith=query)  # Starts with the query
            | Q(name__icontains=f" {query}")  # Space before query
            | Q(name__icontains=f"-{query}")  # Hyphen before query
            | Q(name__icontains=f".{query}"),  # Period before query
        )[: AUTHOR_SUGGESTION_PAGE_SIZE + 1]

    has_more = len(authors) > AUTHOR_SUGGESTION_PAGE_SIZE
    authors = authors[:AUTHOR_SUGGESTION_PAGE_SIZE]  # Trim if there are more

    return render(
        request,
        "partials/author_suggestions.html",
        {"authors": authors, "has_more": has_more},
    )


@smart_login_required
@require_GET  # type: ignore
def library_page(request: HttpRequest) -> HttpResponse:
    """Render the main library page."""
    if not request.user.language:
        return TemplateResponse(request, "library.html", {"show_user_modal": True})
    return TemplateResponse(request, "library.html")
