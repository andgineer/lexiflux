"""Vies for the Lexiflux app."""

from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import models
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.models import CustomUser
from lexiflux.language.translation import get_translator

from .models import Book, BookPage, ReadingHistory, ReadingLoc


def render_page(content: str) -> str:
    """Render the page."""
    words = content.split()  # Split the content into words
    spanned_words = []
    word_index = 0
    for word in words:
        if word == "<br/>":
            spanned_words.append("<br/>")
        else:
            spanned_word = f'<span id="word-{word_index}" class="word">{word}</span>'
            spanned_words.append(spanned_word)
            word_index += 1
    return " ".join(spanned_words)


def redirect_to_reader(request: HttpRequest) -> HttpResponse:
    """Redirect to the 'reader' view."""
    return redirect("reader")


def can_see_book(user: CustomUser, book: Book) -> bool:
    """Check if the user can see the book."""
    return user.is_superuser or book.owner == user or user in book.shared_with.all() or book.public


@login_required  # type: ignore
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
        if not (reading_location := ReadingLoc.objects.filter(user=request.user).first()):
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

    return render(
        request,
        "reader.html",
        {
            "book": book_page.book,
            "page": book_page,
            "top_word": 0,
        },
    )


@login_required  # type: ignore
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
    location(request)

    print(f"Rendering page {page_number} of book {book_code}")
    page_html = render_page(book_page.content)

    return JsonResponse(
        {
            "html": page_html,
            "data": {
                "bookCode": book_code,
                "pageNumber": page_number,
            },
        }
    )


@login_required  # type: ignore
def location(request: HttpRequest) -> HttpResponse:
    """Read location changed."""
    try:
        book_code = request.GET.get("book-code")
        page_number = int(request.GET.get("book-page-number"))
        top_word = int(request.GET.get("top-word", 0))
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


@login_required  # type: ignore
def translate(request: HttpRequest) -> HttpResponse:
    """Translate text.

    full: if true, side panel is visible so we prepare detailed translation materials.
    """
    print("Translating text")
    text = request.GET.get("text")
    book_code = request.GET.get("book-code")
    # active_panel = request.GET.get("active-panel")  # todo: use to call explain / examples / etc
    user_id = request.user.id

    print("Translating", text)
    translator = get_translator(book_code, user_id)
    print("Translator", translator)
    translated = translator.translate(text)
    print("Translated", translated)
    article = f"""<p>{translated}</p>"""  # todo: get article from the translator
    # todo: get LLM explanation if `full`
    return JsonResponse({"translatedText": translated, "article": article})


@login_required  # type: ignore
def profile(request: HttpRequest) -> HttpResponse:
    # if not request.user.is_approved:
    """Profile page."""
    return render(request, "profile.html")


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

    return render(request, "library.html", {"books": books})


@login_required  # type: ignore
@require_POST
def add_to_history(request):
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


def dictionary_content(request: HttpRequest) -> HttpResponse:
    """Fetch or generate dictionary content."""
    content = "Dictionary content goes here."
    return JsonResponse({"content": content})


def explain_content(request: HttpRequest) -> HttpResponse:
    """Fetch or generate explain content."""
    content = "Explain content goes here."
    return JsonResponse({"content": content})


def examples_content(request: HttpRequest) -> HttpResponse:
    """Fetch or generate examples content."""
    content = "Examples content goes here."
    return JsonResponse({"content": content})
