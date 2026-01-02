"""Views for Calibre Smart Device integration."""

import base64
import json
import logging
import os
import tempfile
import uuid
from typing import Any

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from lexiflux.ebook.book_loader_base import BookLoaderBase
from lexiflux.ebook.book_loader_epub import BookLoaderEpub
from lexiflux.ebook.book_loader_html import BookLoaderHtml
from lexiflux.ebook.book_loader_plain_text import BookLoaderPlainText
from lexiflux.models import APIToken, Author, Book, CustomUser, Language

logger = logging.getLogger(__name__)

# Calibre Smart Device Protocol constants
DEVICE_NAME = "Lexiflux"
DEVICE_VERSION = "1.0.0"
PREFERRED_FORMATS = ["epub", "html", "txt"]


def _get_authenticated_user_email(request: HttpRequest) -> str | None:
    """Get authenticated user email from request. Always requires valid token."""
    # For Calibre uploads, we ALWAYS require token authentication
    # skip_auth does NOT bypass API authentication

    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth_header.startswith("Bearer "):
        logger.warning("No Bearer token provided for Calibre upload")
        return None

    token = auth_header[7:]  # Remove 'Bearer ' prefix

    # Validate token against database
    try:
        api_token = APIToken.objects.select_related("user").get(
            token=token,
            is_active=True,
        )

        # Update last used timestamp
        api_token.touch()

        logger.info(f"Calibre upload authenticated for user {api_token.user.email}")
        return api_token.user.email

    except APIToken.DoesNotExist:
        logger.error(f"Invalid or inactive API token: {token[:10]}...")
        return None


@csrf_exempt  # type: ignore[arg-type]
@require_GET  # type: ignore[arg-type]
def calibre_handshake(request: HttpRequest) -> JsonResponse:
    """Handle Calibre device discovery handshake."""
    try:
        # Parse query parameters for device discovery
        stage = request.GET.get("stage", "1")

        if stage == "1":
            # Initial handshake - return device capabilities
            response_data = {
                "stage": 1,
                "device_name": DEVICE_NAME,
                "device_version": DEVICE_VERSION,
                "preferred_formats": PREFERRED_FORMATS,
                "can_stream_books": True,
                "can_receive_books": True,
                "supports_cover_upload": False,
                "supports_annotations": False,
                "password_required": False,  # TODO: Add password support if needed
            }
            logger.info(f"Calibre handshake stage 1: {response_data}")
            return JsonResponse(response_data)

        if stage == "2":
            # Confirm connection
            response_data = {
                "stage": 2,
                "device_name": DEVICE_NAME,
                "status": "connected",
                "session_id": str(uuid.uuid4()),
            }
            logger.info(f"Calibre handshake stage 2: {response_data}")
            return JsonResponse(response_data)

        return JsonResponse({"error": "Invalid handshake stage"}, status=400)

    except Exception as e:  # noqa: BLE001
        logger.error(f"Error in Calibre handshake: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt  # type: ignore[arg-type]
@require_POST  # type: ignore[arg-type]
def calibre_upload_book(request: HttpRequest) -> JsonResponse:
    """Handle book upload from Calibre."""
    try:
        # Check authentication
        user_email = _get_authenticated_user_email(request)
        if user_email is None:
            return JsonResponse({"error": "Authentication required"}, status=401)

        # Handle both form data and JSON uploads
        if request.content_type and "multipart/form-data" in request.content_type:
            # Standard file upload
            return _handle_file_upload(request, user_email)
        # JSON-based chunked upload
        return _handle_json_upload(request, user_email)

    except Exception as e:  # noqa: BLE001
        logger.error(f"Error uploading book from Calibre: {e}")
        return JsonResponse({"error": str(e)}, status=500)


def _handle_file_upload(request: HttpRequest, user_email: str) -> JsonResponse:
    """Handle standard file upload from Calibre."""
    file = request.FILES.get("book_file")
    if not file:
        return JsonResponse({"error": "No file provided"}, status=400)

    # Get metadata from form data
    metadata_json = request.POST.get("metadata", "{}")
    try:
        metadata = json.loads(metadata_json)
    except json.JSONDecodeError:
        metadata = {}

    # Import the book using existing book loaders
    filename = file.name or "uploaded_book.epub"
    book = _import_book_file(file, filename, metadata, user_email)

    logger.info(f"Successfully imported book from Calibre: {book.title}")
    return JsonResponse(
        {
            "status": "success",
            "book_id": book.id,
            "title": book.title,
            "message": f"Book '{book.title}' imported successfully",
        },
    )


def _handle_json_upload(request: HttpRequest, user_email: str) -> JsonResponse:
    """Handle JSON-based chunked upload from Calibre."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    opcode = data.get("opcode")

    if opcode == "UPLOAD_BOOK":
        # Handle book upload with metadata
        book_data = data.get("book_data", {})
        filename = book_data.get("filename", "unknown.epub")
        file_content = book_data.get("content")  # Base64 encoded content
        metadata = data.get("metadata", {})

        if not file_content:
            return JsonResponse({"error": "No book content provided"}, status=400)

        try:
            decoded_content = base64.b64decode(file_content)
        except Exception as e:  # noqa: BLE001
            return JsonResponse({"error": f"Invalid base64 content: {e}"}, status=400)

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=f".{filename.split('.')[-1]}",
        ) as tmp_file:
            tmp_file.write(decoded_content)
            tmp_file.flush()

            # Import the book
            book = _import_book_from_path(tmp_file.name, filename, metadata, user_email)
            try:
                os.unlink(tmp_file.name)
            except Exception:  # noqa: BLE001
                logger.warning(f"Failed to delete temporary file: {tmp_file.name}")

        logger.info(f"Successfully imported book from Calibre JSON: {book.title}")
        return JsonResponse(
            {
                "opcode": "UPLOAD_BOOK_RESPONSE",
                "status": "success",
                "book_id": book.id,
                "title": book.title,
                "message": f"Book '{book.title}' imported successfully",
            },
        )

    return JsonResponse({"error": f"Unknown opcode: {opcode}"}, status=400)


def _import_book_file(file, filename: str, metadata: dict[str, Any], user_email: str) -> Book:  # noqa: PLR0912,C901
    """Import a book from an uploaded file."""
    file_extension = filename.split(".")[-1].lower()

    # Determine book loader class
    book_class: type[BookLoaderBase]
    if file_extension == "txt":
        book_class = BookLoaderPlainText
    elif file_extension == "html":
        book_class = BookLoaderHtml
    elif file_extension == "epub":
        book_class = BookLoaderEpub
    else:
        raise ValueError(f"Unsupported file format: {file_extension}")

    # Save file to temporary location if needed
    if hasattr(file, "temporary_file_path"):
        # File is already on disk
        book_processor = book_class(file.temporary_file_path(), original_filename=filename)
    else:
        # File is in memory, save to disk first
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as tmp_file:
            for chunk in file.chunks():
                tmp_file.write(chunk)
            tmp_file.flush()

            book_processor = book_class(tmp_file.name, original_filename=filename)
            try:
                os.unlink(tmp_file.name)
            except Exception:  # noqa: BLE001
                logger.warning(f"Failed to delete temporary file: {tmp_file.name}")

    # Create book with metadata override if provided
    book = book_processor.create(user_email)

    # Apply Calibre metadata if provided
    if metadata:
        if "title" in metadata and metadata["title"]:
            book.title = metadata["title"]
        if "authors" in metadata and metadata["authors"]:
            # Handle authors properly - create or get Author instances

            author_names = metadata["authors"]
            if author_names:
                # For now, just use the first author
                # You might want to handle multiple authors differently
                author_name = author_names[0] if isinstance(author_names, list) else author_names

                # Get or create the author
                author, created = Author.objects.get_or_create(
                    name=author_name,
                    defaults={"name": author_name},
                )

                book.author = author
                if created:
                    logger.info(f"Created new author: {author_name}")

        if "language" in metadata and metadata["language"]:
            # Try to match language code to existing Language model

            try:
                language = Language.objects.get(google_code=metadata["language"])
                book.language = language
            except Language.DoesNotExist:
                logger.warning(f"Language {metadata['language']} not found in database")

    book.save()
    return book


def _import_book_from_path(  # noqa: C901
    file_path: str,
    filename: str,
    metadata: dict[str, Any],
    user_email: str,
) -> Book:
    """Import a book from a file path."""
    file_extension = filename.split(".")[-1].lower()

    # Determine book loader class
    book_class: type[BookLoaderBase]
    if file_extension == "txt":
        book_class = BookLoaderPlainText
    elif file_extension == "html":
        book_class = BookLoaderHtml
    elif file_extension == "epub":
        book_class = BookLoaderEpub
    else:
        raise ValueError(f"Unsupported file format: {file_extension}")

    book_processor = book_class(file_path, original_filename=filename)
    book = book_processor.create(user_email)

    # Apply Calibre metadata if provided
    if metadata:
        if "title" in metadata and metadata["title"]:
            book.title = metadata["title"]
        if "authors" in metadata and metadata["authors"]:
            author_names = metadata["authors"]
            if author_names:
                # For now, just use the first author
                # You might want to handle multiple authors differently
                author_name = author_names[0] if isinstance(author_names, list) else author_names

                # Get or create the author
                author, created = Author.objects.get_or_create(
                    name=author_name,
                    defaults={"name": author_name},
                )

                book.author = author
                if created:
                    logger.info(f"Created new author: {author_name}")

        if "language" in metadata and metadata["language"]:
            # Try to match language code to existing Language model

            try:
                language = Language.objects.get(google_code=metadata["language"])
                book.language = language
            except Language.DoesNotExist:
                logger.warning(f"Language {metadata['language']} not found in database")

    book.save()
    return book


@csrf_exempt  # type: ignore[arg-type]
@require_GET  # type: ignore[arg-type]
def calibre_status(request: HttpRequest) -> JsonResponse:
    """Return Calibre device status with authentication check."""
    try:
        # Check authentication if token is provided
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        authenticated_user = None

        if auth_header.startswith("Bearer "):
            authenticated_user = _get_authenticated_user_email(request)
            if authenticated_user is None:
                return JsonResponse({"error": "Invalid or expired token"}, status=401)

        # Get basic status information
        book_count = Book.objects.count()
        user_count = CustomUser.objects.count()

        status_data = {
            "device_name": DEVICE_NAME,
            "device_version": DEVICE_VERSION,
            "status": "ready",
            "book_count": book_count,
            "user_count": user_count,
            "preferred_formats": PREFERRED_FORMATS,
            "authenticated": authenticated_user is not None,
            "user_email": authenticated_user,
            "timestamp": str(uuid.uuid4()),  # Simple timestamp/session marker
        }

        return JsonResponse(status_data)

    except Exception as e:  # noqa: BLE001
        logger.error(f"Error getting Calibre status: {e}")
        return JsonResponse({"error": str(e)}, status=500)
