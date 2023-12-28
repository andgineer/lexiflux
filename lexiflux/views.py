"""Vies for the Lexiflux app."""
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST

from lexiflux.language.translation import get_translator

from .models import Book, BookPage, ReaderProfile, ReadingHistory, ReadingPos


@login_required  # type: ignore
def reader(request: HttpRequest) -> HttpResponse:
    """Render book."""
    book_id = request.GET.get("book-id", 1)
    page_number = request.GET.get("page-num", 1)
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
    reader_profile, _ = ReaderProfile.objects.get_or_create(user=request.user)

    books = (
        Book.objects.filter(models.Q(shared_with=request.user) | models.Q(public=True))
        .annotate(
            last_read_time=models.Max(
                "readingprogress__last_read_time",
                filter=models.Q(readingprogress__reader=reader_profile),
            )
        )
        .order_by("-last_read_time")
        .distinct()
    )

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

    ReadingHistory.objects.create(
        user=user,
        book=book,
        page_number=page_number,
        top_word_id=top_word_id,
        read_time=timezone.now(),
    )

    return JsonResponse({"message": "Reading history added successfully"})
