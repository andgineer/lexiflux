"""Vies for the Lexiflux app."""
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import models
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.models import CustomUser
from lexiflux.language.translation import get_translator

from .models import Book, BookPage, ReadingHistory, ReadingPos


def can_see_book(user: CustomUser, book: Book) -> bool:
    """Check if the user can see the book."""
    return user.is_superuser or book.owner == user or user in book.shared_with.all() or book.public


@login_required  # type: ignore
def reader(request: HttpRequest) -> HttpResponse:
    """Render book."""
    book_id = request.GET.get("book-id", 1)
    book = get_object_or_404(Book, id=book_id)
    if not can_see_book(request.user, book):
        return HttpResponse(status=403)

    page_number = request.GET.get("page-num")

    if not page_number:
        reading_position = ReadingPos.objects.filter(book=book, user=request.user).first()
        page_number = reading_position.page_number if reading_position else 1

    print("book_id", book_id, "page_number", page_number)
    book_page = BookPage.objects.get(book_id=book_id, number=page_number)

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
    """Book page."""
    book_id = request.GET.get("book-id", 1)
    page_number = request.GET.get("page-num", 1)
    try:
        book_page = BookPage.objects.get(book_id=book_id, number=page_number)
    except BookPage.DoesNotExist:
        return HttpResponse(f"error: Page {page_number} not found", status=500)
    if not can_see_book(request.user, book_page.book):
        return HttpResponse(status=403)  # Forbidden
    words = book_page.content.split(" ")
    print(book_id, page_number, "words", len(words))
    rendered_html = render_to_string(
        "page.html",
        {
            "book": book_page.book,
            "page": book_page,
            "words": words,
        },
        request,
    )

    return JsonResponse(
        {
            "html": rendered_html,
            "data": {
                "bookId": book_id,
                "pageNum": page_number,
                "words": words,
            },
        }
    )


@login_required  # type: ignore
def position(request: HttpRequest) -> HttpResponse:
    """Read position changed."""
    try:
        book_id = int(request.GET.get("book-id"))
        page_number = int(request.GET.get("page-num"))
        top_word = int(request.GET.get("top-word", 0))
    except (TypeError, ValueError, KeyError):
        return HttpResponse("Invalid or missing parameters", status=400)

    if not can_see_book(request.user, Book.objects.get(id=book_id)):
        return HttpResponse(status=403)  # Forbidden

    ReadingPos.update_user_pos(
        user=request.user, book_id=book_id, page_number=page_number, top_word_id=top_word
    )
    return HttpResponse(status=200)


@login_required  # type: ignore
def translate(request: HttpRequest) -> HttpResponse:
    """Translate text."""
    print("Translating text")
    text = request.GET.get("text", 1)  # todo: None
    book_id = request.GET.get("book-id", 1)  # todo: None
    user_id = request.user.id

    # if not book_id:
    #     return JsonResponse({"error": "Book ID is required"}, status=400)

    print("Translating", text)
    translator = get_translator(book_id, user_id)
    print("Translator", translator)
    translated = translator.translate(text)
    print("Translated", translated)
    article = """<p>Hello</p>"""  # Example content
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
            latest_reading_time=models.Max(
                "readingpos__last_read_time", filter=models.Q(readingpos__user=request.user)
            )
        )
        .order_by("-latest_reading_time", "title")
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
    """Add the position to History."""
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
    book_id = request.GET.get("book_id")
    book = get_object_or_404(Book, id=book_id)

    if not can_see_book(request.user, book):
        return HttpResponse(status=403)  # Forbidden

    # Additional details like pages, author, etc., can be added here
    context = {
        "book": book,
        # 'pages': book.pages.all(),  # Uncomment if you want to show pages
        # 'author': book.author,  # Uncomment if you want to show author details
    }

    return render(request, "book.html", context)
