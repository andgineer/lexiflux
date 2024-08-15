"""Views for the reader page."""

import os
from typing import List
from urllib.parse import unquote

from bs4 import BeautifulSoup
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from lexiflux.decorators import smart_login_required
from lexiflux.models import (
    BookPage,
    CustomUser,
    Book,
    ReadingLoc,
    LanguagePreferences,
    ReadingHistory,
    BookImage,
)


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


def set_images_sources(content: str, book: Book) -> str:
    """Replace image sources with the Django view URL."""
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
                    print(f"Warning: Image not found in database for src: {original_src}")
                    continue

            new_src = reverse(
                "serve_book_image",
                kwargs={"book_code": book.code, "image_filename": image.filename},
            )
            img["src"] = new_src

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
    return set_images_sources("".join(result), page_db.book)


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
    """
    book_code = request.GET.get("book-code")
    page_number = request.GET.get("book-page-number")
    book = Book.objects.filter(code=book_code).first() if book_code else None
    if not book:
        if book_code:
            print(f"Book {book_code} not found")
        reading_location = (
            ReadingLoc.objects.filter(user=request.user).order_by("-updated").first()
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

    print(f"Opening book {book_code} at page {page_number} for user {request.user.username}")
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

    return render(
        request,
        "reader.html",
        {
            "book": book_page.book,
            "page": book_page,
            "lexical_articles": lexical_articles,
            "top_word": reading_location.word if reading_location else 0,
        },
    )


@smart_login_required  # type: ignore
def page(request: HttpRequest) -> HttpResponse:
    """Book page.

    In addition to book and page num should include top word id to save the location.
    """
    book_code = request.GET.get("book-code")
    page_number = request.GET.get("book-page-number")
    try:
        page_number = int(page_number)
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

    # Update the reading location
    location(request)  # type: ignore

    cache_key = f"page_html_{book_code}_{page_number}"
    page_html = cache.get(cache_key)
    if page_html is None:
        print(f"Rendering page {page_number} of book {book_code}")
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


@smart_login_required  # type: ignore
def location(request: HttpRequest) -> HttpResponse:
    """Read location changed."""
    try:
        book_code = request.GET.get("book-code") or request.POST.get("book-code")
        page_number = int(
            request.GET.get("book-page-number") or request.POST.get("book-page-number")
        )
        top_word = int(request.GET.get("top-word", 0) or request.POST.get("top-word", 0))
        if not book_code:
            raise ValueError("book-code is missing")
    except (TypeError, ValueError, KeyError):
        return HttpResponse("Invalid or missing parameters", status=400)

    book = Book.objects.get(code=book_code)
    if not can_see_book(request.user, book):
        return HttpResponse(status=403)  # Forbidden

    ReadingLoc.update_reading_location(
        user=request.user, book_id=book.id, page_number=page_number, top_word_id=top_word
    )
    return HttpResponse(status=200)


@smart_login_required
@require_POST  # type: ignore
def add_to_history(request: HttpRequest) -> JsonResponse:
    """Add the location to History."""
    user = request.user

    book_id = request.POST.get("book_id")
    page_number = request.POST.get("page_number")
    top_word_id = request.POST.get("top_word_id")

    try:
        book_id = int(book_id)
        page_number = int(page_number)
        top_word_id = int(top_word_id)
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid input"}, status=400)

    book = get_object_or_404(Book, id=book_id)
    if not can_see_book(request.user, book):
        return HttpResponse(status=403)  # Forbidden

    ReadingHistory.objects.create(
        user=user,
        book=book,
        page_number=page_number,
        top_word_id=top_word_id,
        read_time=timezone.now(),
    )

    return JsonResponse({"message": "Reading history added successfully"})
