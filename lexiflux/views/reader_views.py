"""Views for the reader page."""

import json
import logging
import os
import re
from typing import List
from urllib.parse import unquote

from bs4 import BeautifulSoup
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST

from lexiflux.decorators import smart_login_required
from lexiflux.models import (
    BookPage,
    CustomUser,
    Book,
    ReadingLoc,
    LanguagePreferences,
    BookImage,
    ReaderSettings,
)


log = logging.getLogger()


def normalize_path(path: str) -> str:
    """Normalize the image path by removing '..' and extra '/'."""
    path = unquote(path)
    components = path.split("/")
    normalized: List[str] = []
    for component in components:
        if component == "." or not component:
            continue
        if component == "..":
            if normalized:
                normalized.pop()
        else:
            normalized.append(component)
    return "/".join(normalized)


def set_sources(content: str, book: Book) -> str:
    """Replace image sources / link targets with the Django view URL."""
    soup = BeautifulSoup(content, "html.parser")

    for img in soup.find_all("img"):
        if "src" in img.attrs:
            original_src = img["src"]

            normalized_src = normalize_path(original_src)

            # Try to find the image in the database
            try:
                # First, try with the full normalized path
                image = BookImage.objects.get(book=book, filename=normalized_src)
            except BookImage.DoesNotExist:
                try:
                    # If not found, try with just the filename
                    image = BookImage.objects.get(
                        book=book, filename__endswith=os.path.basename(normalized_src)
                    )
                except BookImage.DoesNotExist:
                    log.warning(f"Warning: Image not found in database for src: {original_src}")
                    continue

            new_src = reverse(
                "serve_book_image",
                kwargs={"book_code": book.code, "image_filename": image.filename},
            )
            img["src"] = new_src

    # Retarget internal links
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.startswith(("http://", "https://", "ftp://", "mailto:")):
            continue  # Skip external links

        normalized_href = normalize_path(href)
        link["href"] = "javascript:void(0);"
        link["data-href"] = normalized_href

    return str(soup)


def render_page(page_db: BookPage) -> str:
    """Render the page using the parsed word."""
    content = page_db.content
    result = []
    last_end = 0

    for word_idx, word_pos in enumerate(page_db.words):
        # Add text between words (if any)
        start, end = word_pos
        if start > last_end:
            result.append(content[last_end:start])

        # Add the word with span
        word = content[start:end]
        result.append(f'<span id="word-{word_idx}" class="word">{word}</span>')
        last_end = end

    # Add any remaining text after the last word
    if last_end < len(content):
        result.append(content[last_end:])
    return set_sources("".join(result), page_db.book)


def redirect_to_reader(request: HttpRequest) -> HttpResponse:
    """Redirect to the 'reader' view."""
    return redirect("reader")


def can_see_book(user: CustomUser, book: Book) -> bool:
    """Check if the user can see the book."""
    return user.is_superuser or book.owner == user or user in book.shared_with.all() or book.public


@smart_login_required  # type: ignore
def reader(request: HttpRequest) -> HttpResponse:
    """Open the book in reader.

    If the book code not given open the latest book.
    Send jump status to set jump buttons active/inactive.
    """
    book_code = request.GET.get("book-code")
    page_number = request.GET.get("book-page-number")
    book = Book.objects.filter(code=book_code).first() if book_code else None
    if not book:
        if book_code:
            log.warning(f"Book {book_code} not found")
        reading_location = (
            ReadingLoc.objects.filter(user=request.user).order_by("-last_access").first()
        )
        if not reading_location:
            return redirect("library")  # Redirect if the user has no reading history

        book = reading_location.book
        book_code = book.code  # Update book_code to be used in the response
        page_number = reading_location.page_number
    # Security check to ensure the user is authorized to view the book
    if not can_see_book(request.user, book):
        return HttpResponse("Forbidden", status=403)

    if not page_number:
        # if the book-code is provided but book-page-number is not: first page or last read page
        reading_location = ReadingLoc.objects.filter(book=book, user=request.user).first()
        page_number = reading_location.page_number if reading_location else 1
    else:
        page_number = int(page_number)  # Ensure page_number is an integer

    log.info(f"Opening book {book_code} at page {page_number} for user {request.user.username}")
    book_page = BookPage.objects.get(book=book, number=page_number)

    language_preferences = LanguagePreferences.get_or_create_language_preferences(
        request.user, book.language
    )
    # Minimize user's confusion:
    # we expect when he goes to the Language preferences he wants to change the preferences
    # for the language of the book he just read. Language preferences editor could be very
    # confusing if you do not notice for which language you are changing the preferences.
    if request.user.default_language_preferences != language_preferences:
        request.user.default_language_preferences = language_preferences
        request.user.save()
    lexical_articles = language_preferences.get_lexical_articles()

    reading_location = ReadingLoc.get_or_create_reading_loc(user=request.user, book=book)
    is_first_jump = reading_location.current_jump <= 0
    is_last_jump = reading_location.current_jump == len(reading_location.jump_history) - 1
    log.info(
        f"Jump status: book {book_code}, is_first_jump {is_first_jump}, "
        f"is_last_jump {is_last_jump}"
    )

    reader_settings = ReaderSettings.get_settings(
        user=request.user,
        book=book,
    )

    return render(
        request,
        "reader.html",
        {
            "book": book_page.book,
            "page": book_page,
            "lexical_articles": lexical_articles,
            "top_word": reading_location.word if reading_location else 0,
            "is_first_jump": is_first_jump,
            "is_last_jump": is_last_jump,
            "settings": reader_settings,
        },
    )


@smart_login_required  # type: ignore
def page(request: HttpRequest) -> HttpResponse:
    """Book page."""
    book_code = request.GET.get("book-code")
    page_number = request.GET.get("book-page-number")
    book = Book.objects.filter(code=book_code).first() if book_code else None
    if not book:
        return HttpResponse("error: Book not found", status=404)
    try:
        page_number = int(page_number)
        if page_number < 1:
            page_number = 1
        elif page_number > book.pages.count():
            page_number = book.pages.count()
        book_page = BookPage.objects.filter(book__code=book_code, number=page_number).first()
        if not book_page:
            raise BookPage.DoesNotExist
    except (BookPage.DoesNotExist, ValueError):
        return HttpResponse(
            f"error: Page {page_number} not found in book '{book_code}'", status=500
        )
    # check access
    if not can_see_book(request.user, book_page.book):
        return HttpResponse(status=403)

    cache_key = f"page_html_{book_code}_{page_number}"
    page_html = cache.get(cache_key)
    if page_html is None:
        log.info(f"Rendering page {page_number} of book {book_code}")
        page_html = render_page(book_page)
        cache.set(cache_key, page_html, timeout=3600)  # Cache for 1 hour

    return JsonResponse(
        {
            "html": page_html,
            "data": {
                "bookCode": book_code,
                "pageNumber": page_number,
            },
        }
    )


@smart_login_required  # type: ignore
def serve_book_image(request, book_code, image_filename):
    """Serve the book image."""
    book = get_object_or_404(Book, code=book_code)
    if not can_see_book(request.user, book):
        return HttpResponse("Forbidden", status=403)

    image = get_object_or_404(BookImage, book=book, filename=image_filename)
    return HttpResponse(image.image_data, content_type=image.content_type)


@smart_login_required
@require_POST  # type: ignore
def location(request: HttpRequest) -> HttpResponse:
    """Read location changed."""
    try:
        book_code = request.POST.get("book-code")
        page_number = int(request.POST.get("book-page-number"))
        top_word = int(request.POST.get("top-word", 0))
        if not book_code:
            raise ValueError("book-code is missing")
    except (TypeError, ValueError, KeyError):
        return HttpResponse("Invalid or missing parameters", status=400)

    log.info(f"Location changed: book {book_code}, page {page_number}, top word {top_word}")
    book = Book.objects.get(code=book_code)
    if not can_see_book(request.user, book):
        return HttpResponse(status=403)  # Forbidden

    ReadingLoc.update_reading_location(
        user=request.user, book_id=book.id, page_number=page_number, top_word_id=top_word
    )
    return HttpResponse(status=200)


@smart_login_required
@require_POST  # type: ignore
def jump(request: HttpRequest) -> HttpResponse:
    """Jump to a specific location in the book."""
    try:
        book_code = request.POST.get("book-code")
        page_number = int(request.POST.get("book-page-number"))
        top_word = int(request.POST.get("top-word"))

        if not book_code:
            return JsonResponse({"error": "Missing book code"}, status=400)

        book = get_object_or_404(Book, code=book_code)
        if not can_see_book(request.user, book):
            return HttpResponse("Forbidden", status=403)
        reading_loc = ReadingLoc.get_or_create_reading_loc(user=request.user, book=book)
        reading_loc.jump(page_number, top_word)

        return JsonResponse({"success": True})
    except ValueError:
        return JsonResponse({"error": "Invalid page number or top word"}, status=400)


@smart_login_required
@require_POST  # type: ignore
def jump_back(request: HttpRequest) -> HttpResponse:
    """Jump back to the previous location in the book."""
    book_code = request.POST.get("book-code")
    if not book_code:
        return JsonResponse({"error": "Missing book code"}, status=400)

    book = get_object_or_404(Book, code=book_code)
    if not can_see_book(request.user, book):
        return HttpResponse("Forbidden", status=403)
    reading_loc = ReadingLoc.get_or_create_reading_loc(user=request.user, book=book)

    page_number, word = reading_loc.jump_back()
    return JsonResponse({"success": True, "page_number": page_number, "word": word})


@smart_login_required
@require_POST  # type: ignore
def jump_forward(request: HttpRequest) -> HttpResponse:
    """Jump forward to the next location in the book."""
    book_code = request.POST.get("book-code")
    if not book_code:
        return JsonResponse({"error": "Missing book code"}, status=400)

    book = get_object_or_404(Book, code=book_code)
    if not can_see_book(request.user, book):
        return HttpResponse("Forbidden", status=403)
    reading_loc = ReadingLoc.get_or_create_reading_loc(user=request.user, book=book)

    page_number, word = reading_loc.jump_forward()
    return JsonResponse({"success": True, "page_number": page_number, "word": word})


@smart_login_required  # type: ignore
def get_jump_status(request: HttpRequest) -> HttpResponse:
    """Get the status of the jump history."""
    book_code = request.GET.get("book-code")
    if not book_code:
        return JsonResponse({"error": "Missing book code"}, status=400)

    book = get_object_or_404(Book, code=book_code)
    if not can_see_book(request.user, book):
        return HttpResponse("Forbidden", status=403)

    reading_loc = ReadingLoc.get_or_create_reading_loc(user=request.user, book=book)

    is_first_jump = reading_loc.current_jump <= 0
    is_last_jump = reading_loc.current_jump == len(reading_loc.jump_history) - 1
    log.info(
        f"Jump status: book {book_code}, is_first_jump {is_first_jump}, "
        f"is_last_jump {is_last_jump}"
    )

    return JsonResponse({"is_first_jump": is_first_jump, "is_last_jump": is_last_jump})


@smart_login_required
@require_POST  # type: ignore
def link_click(request: HttpRequest) -> HttpResponse:
    """Handle a link click in the book."""
    book_code = request.POST.get("book-code")
    link = request.POST.get("link")

    book = get_object_or_404(Book, code=book_code)

    # Get the page number from the anchor_map
    page_info = book.anchor_map.get(link)
    log.info(f"Link clicked: {link}, page_info: {page_info}")

    if not page_info:
        return JsonResponse({"success": False, "error": f"Link {link} not found in anchor map"})

    new_page_number = page_info["page"]
    new_word = page_info.get("word", 0)  # Default to 0 if 'word' is not provided

    # Get or create the reading location for this user and book
    reading_loc = ReadingLoc.get_or_create_reading_loc(request.user, book)

    # Use the jump method to update the reading location and jump history
    reading_loc.jump(new_page_number, new_word)

    return JsonResponse({"success": True, "page_number": new_page_number, "word": new_word})


@smart_login_required
@require_POST  # type: ignore
def search(request: HttpRequest) -> HttpResponse:
    """Search for a term in the book."""
    try:
        data = json.loads(request.body)
        book_code = data.get("book-code")
        search_term = data.get("search-term")

        if not book_code or not search_term:
            return JsonResponse({"error": "Missing book code or search term"}, status=400)

        book = get_object_or_404(Book, code=book_code)
        if not can_see_book(request.user, book):
            return HttpResponse("Forbidden", status=403)

        # Perform the search
        pages = BookPage.objects.filter(book=book, content__icontains=search_term)
        results = []

        for page_to_search in pages:
            # Find all occurrences of the search term in the page content
            start_indices = [
                m.start()
                for m in re.finditer(re.escape(search_term), page_to_search.content, re.IGNORECASE)
            ]

            for start_index in start_indices:
                # Get the context around the search term
                context_start = max(0, start_index - 30)
                context_end = min(len(page_to_search.content), start_index + len(search_term) + 30)
                context = page_to_search.content[context_start:context_end]

                # Find the word index
                word_index = sum(1 for w in page_to_search.words if w[0] < start_index)

                results.append(
                    {
                        "pageNumber": page_to_search.number,
                        "wordIndex": word_index,
                        "context": context,
                    }
                )

        # Limit to 10 results
        results = results[:10]

        return JsonResponse(results, safe=False)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:  # pylint: disable=broad-except
        return JsonResponse({"error": str(e)}, status=500)


def get_reader_settings_fields() -> List[str]:
    """Get all fields from ReaderSettings model except user and book."""
    return [
        field.name
        for field in ReaderSettings._meta.get_fields()
        if field.name not in ["id", "user", "book"]
    ]


@smart_login_required  # type: ignore
def load_reader_settings(request: HttpRequest) -> HttpResponse:  # pragma: no cover
    """Load reader settings for a user and specific book.

    Obsolete - we load reader settings as part of the reader view.

    Query Parameters:
        book_code (required): The unique code of the book

    Returns:
        JsonResponse containing reader settings including:
        - font_size
        - font_family
        - other future settings
    """
    try:
        book_code = request.GET.get("book_code")
        if not book_code:
            return JsonResponse({"error": "Book code is required"}, status=400)

        book = Book.objects.get(code=book_code)
        settings_dict = ReaderSettings.get_settings(user=request.user, book=book)

        return JsonResponse(settings_dict)

    except Book.DoesNotExist:
        return JsonResponse({"error": "Book not found"}, status=404)
    except Exception as e:  # pylint: disable=broad-except
        log.error(f"Error loading reader settings: {str(e)}")
        return JsonResponse({"error": "Failed to load settings"}, status=500)


@smart_login_required
@require_POST  # type: ignore
def save_reader_settings(request: HttpRequest) -> HttpResponse:
    """Save reader settings for a user and specific book.

    POST Parameters:
        book_code (required): The unique code of the book
        Any field from ReaderSettings model can be provided

    Returns:
        HttpResponse with appropriate status code
    """
    try:
        book_code = request.POST.get("book_code")
        if not book_code:
            return JsonResponse({"error": "Book code is required"}, status=400)

        book = Book.objects.get(code=book_code)

        # Pass all provided settings to the model
        settings = dict(request.POST.items())
        settings.pop("book_code")  # Remove book_code from settings dict

        if not settings:
            return JsonResponse({"error": "No settings provided"}, status=400)

        ReaderSettings.save_settings(user=request.user, reader_settings=settings, book=book)

        return HttpResponse(status=200)

    except Book.DoesNotExist:
        return JsonResponse({"error": "Book not found"}, status=404)
    except ValidationError as e:
        log.error(f"Validation error saving reader settings: {str(e)}")
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:  # pylint: disable=broad-except
        log.error(f"Error saving reader settings: {str(e)}")
        return JsonResponse({"error": "Failed to save settings"}, status=500)
