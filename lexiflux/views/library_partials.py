"""Library partial views."""

from typing import Type, Dict, Any

from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import TemporaryUploadedFile
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, render
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


@smart_login_required
@require_GET  # type: ignore
def library_page(request: HttpRequest) -> HttpResponse:
    """Render the main library page."""
    return render(request, "library.html")


@smart_login_required
@require_GET  # type: ignore
def books_list(request: HttpRequest) -> HttpResponse:
    """Return the paginated books list partial."""
    if request.user.is_superuser:
        books_query = Book.objects.all()
    else:
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

    page_number = request.GET.get("page", 1)
    paginator = Paginator(books_query, 10)
    books_page = paginator.get_page(page_number)

    for book in books_page:
        book.formatted_last_read = book.format_last_read(request.user)
        book.last_position_percent = book.reading_loc(request.user).last_position_percent

    return render(request, "partials/books_list.html", {"books": books_page})


@method_decorator(smart_login_required, name="dispatch")
class EditBookModalPartial(TemplateView):  # type: ignore
    """Edit book modal partial view."""

    template_name = "partials/book_modal.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        book_id = self.kwargs.get("book_id")
        book = get_object_or_404(Book, id=book_id)

        context.update(
            {
                "book": book,
                "is_new": self.request.GET.get("is_new", False),
                "languages": Language.objects.all(),
            }
        )
        return context  # type: ignore

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Update book details."""
        book = get_object_or_404(Book, id=kwargs["book_id"])
        if book.owner != request.user and not request.user.is_superuser:
            return HttpResponse("Unauthorized", status=403)

        try:
            book.title = request.POST.get("title", book.title)
            author_name = request.POST.get("author", book.author.name)
            author, _ = Author.objects.get_or_create(name=author_name)
            book.author = author

            language_code = request.POST.get("language", book.language.google_code)
            language = Language.objects.get(google_code=language_code)
            book.language = language

            book.save()

            # Return success response that closes modal and refreshes book list
            return HttpResponse("""
                <script>
                    document.querySelector('#editBookModal').addEventListener('hidden.bs.modal', function() {
                        htmx.trigger('#booksList', 'refresh');
                    });
                    bootstrap.Modal.getInstance(document.querySelector('#editBookModal')).hide();
                </script>
            """)

        except Exception as e:  # pylint: disable=broad-except
            context = self.get_context_data()
            context["error_message"] = str(e)
            return TemplateResponse(request, self.template_name, context)


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
            return JsonResponse({"error": "Unsupported file format"}, status=400)

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

        # Redirect to edit modal for the new book
        return TemplateResponse(
            request,
            "partials/book_modal.html",
            {"book": book, "is_new": True, "languages": Language.objects.all()},
        )

    except Exception as e:  # pylint: disable=broad-except
        return TemplateResponse(request, "partials/import_modal.html", {"error_message": str(e)})


@smart_login_required  # type: ignore
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
