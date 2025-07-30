import io
import json
import logging
import tempfile
import zipfile

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import TemporaryUploadedFile
from django.core.validators import URLValidator
from django.http import HttpRequest, HttpResponse, JsonResponse
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
    context = {
        "skip_auth": settings.lexiflux.skip_auth,
    }
    return render(request, "partials/import_modal.html", context)


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


@smart_login_required
@require_GET  # type: ignore
def download_calibre_plugin(request: HttpRequest) -> HttpResponse:
    """Generate and download Calibre plugin with API token."""
    import os

    from django.conf import settings as django_settings

    from lexiflux.models import APIToken

    # Get the calibre_plugin directory path
    calibre_plugin_dir = os.path.join(
        django_settings.BASE_DIR,
        "lexiflux",
        "calibre_plugin",
    )

    # Ensure the directory exists
    if not os.path.exists(calibre_plugin_dir):
        raise ValueError(
            "Calibre plugin directory not found. "
            "Please create the calibre_plugin directory with the plugin files.",
        )

    # Get server URL from request
    server_url = request.build_absolute_uri("/")[:-1]  # Remove trailing slash

    # Generate API token for this user
    api_token_obj = APIToken.generate_for_user(request.user, name="Calibre Plugin")
    api_token = api_token_obj.token

    logger.info(f"Generated Calibre plugin token for user {request.user.email}")

    # Create ZIP file in memory
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # Walk through the calibre_plugin directory
        for root, _dirs, files in os.walk(calibre_plugin_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # Calculate relative path for ZIP
                arcname = os.path.relpath(file_path, calibre_plugin_dir)

                # Read file content
                with open(file_path, "rb") as f:
                    content = f.read()

                # If it's __init__.py, set server-specific defaults
                if file == "__init__.py":
                    # Constants for replacement - must match exactly what's in __init__.py
                    default_server_url_placeholder = (
                        "'server_url': 'https://your-lexiflux-server.com'"
                    )
                    default_api_token_placeholder = "'api_token': ''"  #  noqa: S105

                    content_str = content.decode("utf-8")
                    # Replace default server URL with actual server URL
                    content_str = content_str.replace(
                        default_server_url_placeholder,
                        f"'server_url': '{server_url}'",
                    )
                    # Set the API token as default if provided
                    if api_token:
                        content_str = content_str.replace(
                            default_api_token_placeholder,
                            f"'api_token': '{api_token}'",
                        )
                    content = content_str.encode("utf-8")

                # Add file to ZIP
                zip_file.writestr(arcname, content)

        # Ensure plugin-import-name file exists
        import_name_file = "plugin-import-name-lexiflux.txt"
        if import_name_file not in [
            f for _, _, files in os.walk(calibre_plugin_dir) for f in files
        ]:
            # Create empty file if it doesn't exist
            zip_file.writestr(import_name_file, "")

    zip_buffer.seek(0)

    response = HttpResponse(zip_buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="Lexiflux_Calibre_Plugin.zip"'
    return response


@require_POST
@smart_login_required  # type: ignore
def generate_api_token(request: HttpRequest) -> JsonResponse:
    """Generate a new API token for the user, removing old ones with the same name."""
    try:
        from lexiflux.models import APIToken

        data = json.loads(request.body)
        name = data.get("name", "API Token")

        # Remove existing tokens with the same name for this user
        old_tokens_count = APIToken.objects.filter(user=request.user, name=name).count()
        APIToken.objects.filter(user=request.user, name=name).delete()

        # Generate new token
        api_token_obj = APIToken.generate_for_user(request.user, name=name)

        logger.info(
            f"Generated new API token '{name}' for user {request.user.email}, "
            f"removed {old_tokens_count} old tokens",
        )

        return JsonResponse(
            {
                "success": True,
                "token": api_token_obj.token,
                "name": name,
                "replaced_count": old_tokens_count,
            },
        )

    except Exception as e:  # noqa: BLE001
        logger.error(f"Error generating API token: {e}")
        return JsonResponse(
            {
                "success": False,
                "error": "Failed to generate token",
            },
            status=500,
        )
