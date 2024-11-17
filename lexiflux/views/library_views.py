"""Views for the library and Book pages."""

import json
import logging

from django.http import HttpRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View

from lexiflux.models import Book, Author, Language
from lexiflux.decorators import smart_login_required


logger = logging.getLogger(__name__)


@method_decorator(smart_login_required, name="dispatch")
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
                    "code": book.code,
                }
            )
        except Book.DoesNotExist:
            return JsonResponse({"error": "Book not found"}, status=404)

    def put(self, request: HttpRequest, book_id: int) -> JsonResponse:
        """Update book details."""
        try:
            book = Book.objects.get(id=book_id)
            try:
                data = json.loads(request.body)
                logger.info("Updating book %s with JSON data: %s", book_id, data)
            except json.JSONDecodeError:
                data = request.POST
                logger.info("Updating book %s with form data: %s", book_id, data)

            book.owner = request.user

            book.title = data.get("title", book.title)

            author_name = data.get("author", book.author.name)
            author, created = Author.objects.get_or_create(name=author_name)
            logger.info("Author after get_or_create: %s (created: %s)", author.name, created)

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

    def delete(self, request: HttpRequest, book_id: int) -> JsonResponse:
        """Delete a book."""
        try:
            book = Book.objects.get(id=book_id)
            if book.owner and (book.owner != request.user and not request.user.is_superuser):
                return JsonResponse(
                    {"error": "You don't have permission to delete this book"}, status=403
                )
            book.delete()
            return JsonResponse({"success": "Book deleted successfully"})
        except Book.DoesNotExist:
            return JsonResponse({"error": "Book not found"}, status=404)
        except Exception as e:  # pylint: disable=broad-except
            return JsonResponse({"error": str(e)}, status=500)
