import logging
import tempfile

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import TemporaryUploadedFile
from django.core.validators import URLValidator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from lexiflux.decorators import smart_login_required
from lexiflux.ebook.book_loader_base import BookLoaderBase
from lexiflux.ebook.book_loader_epub import BookLoaderEpub
from lexiflux.ebook.book_loader_html import BookLoaderHtml
from lexiflux.ebook.book_loader_plain_text import BookLoaderPlainText
from lexiflux.ebook.book_loader_url import BookLoaderURL
from lexiflux.lexiflux_settings import settings
from lexiflux.models import Book, Language
from lexiflux.views.library_views import logger


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
        import_type = request.POST.get("importType", "file")

        if import_type == "file":
            book = import_file(request)
        elif import_type == "url":
            book = import_url(request)
        elif import_type == "paste":
            book = import_clipboard(request)
        else:
            raise ValueError(f"Unknown import type: {import_type}")

        context = {
            "book": book,
            "languages": Language.objects.all(),
            "require_delete_confirmation": False,
            "show_delete_button": True,
            "skip_auth": settings.lexiflux.skip_auth,
        }
        return HttpResponse(f"""
            <script>
                document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
                htmx.trigger('body', 'show-edit-modal');
            </script>
            {render(request, "partials/book_modal.html", context).content.decode("utf-8")}
        """)

    except Exception as e:  # noqa: BLE001
        logging.exception("Error importing book")
        context = {
            "error_message": str(e),
            "importType": request.POST.get("importType", "file"),
            "cleaning_level": request.POST.get(
                "cleaning_level",
                "moderate",
            ),  # Preserve selected cleaning level
        }

        if request.POST.get("importType") == "file" and request.FILES.get("file"):
            context["last_filename"] = request.FILES.get("file").name
        elif request.POST.get("importType") == "url" and request.POST.get("url"):
            context["last_url"] = request.POST.get("url")
        elif request.POST.get("importType") == "paste" and request.POST.get("pasted_content"):
            context["last_paste_length"] = len(request.POST.get("pasted_content"))

        return render(request, "partials/import_modal.html", context)


def import_file(request: HttpRequest) -> Book:
    file = request.FILES.get("file")
    if not file:
        raise ValueError("No file provided")
    original_filename = file.name
    file_extension = original_filename.split(".")[-1].lower()
    book_class: type[BookLoaderBase]
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
            file.temporary_file_path(),
            original_filename=original_filename,
        )
        book = book_processor.create(request.user.email)
        book.save()
    else:
        # in-memory, save on disk
        with tempfile.NamedTemporaryFile(delete=True) as tmp_file:
            for chunk in file.chunks():
                tmp_file.write(chunk)
            tmp_file.flush()

            book_processor = book_class(tmp_file.name, original_filename=original_filename)
            book = book_processor.create(request.user.email)
            book.save()
    return book


def import_clipboard(request: HttpRequest) -> Book:
    pasted_content = request.POST.get("pasted_content")
    if not pasted_content or not pasted_content.strip():
        raise ValueError("No content pasted")
    # Get format from the form
    paste_format = request.POST.get("paste_format", "txt").lower()
    if paste_format not in ["txt", "html"]:
        paste_format = "txt"  # Default to txt if invalid value
    # Save the pasted content to a temporary file with appropriate extension
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{paste_format}") as tmp_file:
        tmp_file.write(pasted_content.encode("utf-8"))
        tmp_file.flush()

        # Select the appropriate loader based on format
        if paste_format == "txt":
            book_class = BookLoaderPlainText
            original_filename = "pasted_text.txt"
        else:
            book_class = BookLoaderHtml
            original_filename = "pasted_content.html"

        logger.info(f"Pasted content ({paste_format}): {pasted_content[:200]}...")

        try:
            book_processor = book_class(
                tmp_file.name,
                original_filename=original_filename,
            )
            book = book_processor.create(request.user.email)
            book.save()
        finally:
            # Make sure we clean up the temporary file
            import os

            try:
                os.unlink(tmp_file.name)
            except Exception:  # noqa: BLE001
                logger.warning(f"Failed to delete temporary file: {tmp_file.name}")
    return book


def import_url(request: HttpRequest) -> Book:
    url = request.POST.get("url")
    if not url:
        raise ValueError("No URL provided")
    validator = URLValidator()
    try:
        validator(url)
    except ValidationError as e:
        raise ValueError("Invalid URL format") from e
    # Get cleaning level with a default of "moderate"
    cleaning_level = request.POST.get("cleaning_level", "moderate")
    if cleaning_level not in ["aggressive", "moderate", "minimal"]:
        cleaning_level = "moderate"  # Default to moderate if invalid value
    book_processor = BookLoaderURL(url, cleaning_level=cleaning_level)
    book = book_processor.create(request.user.email)
    book.save()
    return book
