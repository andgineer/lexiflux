"""View for searching for a term in a book."""

import re
from typing import List
from dataclasses import dataclass
from html import escape
from bs4 import BeautifulSoup
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from lexiflux.decorators import smart_login_required
from lexiflux.models import Book, BookPage, normalize_for_search

MAX_SEARCH_RESULTS = 10


def strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text()  # type: ignore


@dataclass
class SearchResult:
    """Represent a single search result."""

    page_number: int
    context: str


def get_searchable_pages(book: Book, search_term: str, limit: int) -> List[BookPage]:
    """Get pages that contain the search term."""
    normalized_term = normalize_for_search(search_term)
    return BookPage.objects.filter(  # type: ignore
        book=book, normalized_content__icontains=normalized_term
    ).only("number", "content")[:limit]


def find_word_boundary(text: str, pos: int, direction: int) -> int:
    """Find word boundary in given direction (-1 for left, 1 for right)."""
    while 0 <= pos < len(text) and not text[pos].isspace():
        pos += direction
    return max(0, min(pos, len(text) - 1))


def get_context_boundaries(
    content: str, word_start: int, word_end: int, context_words: int = 5
) -> tuple[int, int]:
    """Get the start and end positions for context around a word."""
    context_start = word_start
    context_end = word_end

    # Get words before
    for _ in range(context_words):
        while context_start > 0 and content[context_start - 1].isspace():
            context_start -= 1
        temp_pos = find_word_boundary(content, context_start - 1, -1)
        if temp_pos <= 0:
            break
        context_start = temp_pos + 1

    # Get words after
    for _ in range(context_words):
        while context_end < len(content) and content[context_end].isspace():
            context_end += 1
        temp_pos = find_word_boundary(content, context_end, 1)
        if temp_pos >= len(content):
            break
        context_end = temp_pos

    return context_start, context_end


def create_highlighted_context(context: str, term_start: int, term_length: int) -> str:
    """Create HTML-safe highlighted context."""
    context = escape(context)
    return (
        f"{context[:term_start]}"
        f'<span class="bg-warning">'
        f"{context[term_start:term_start + term_length]}"
        f"</span>"
        f"{context[term_start + term_length:]}"
    )


def find_matches_in_page(  # pylint: disable=too-many-locals
    page: BookPage, search_term: str, whole_words: bool, max_results: int
) -> List[SearchResult]:
    """Find all matches of search_term in the page."""
    results = []
    content = strip_html(page.content)
    search_term_norm = normalize_for_search(search_term)

    # Split into words on any non-word characters
    words = re.findall(r"\b\w+\b", content)

    i = 0
    while i < len(words):
        word_norm = normalize_for_search(words[i])
        is_match = (
            (word_norm == search_term_norm) if whole_words else (search_term_norm in word_norm)
        )

        if is_match:
            # Get context (5 words before and after)
            start = max(0, i - 5)
            end = min(len(words), i + 6)
            context = " ".join(words[start:end])
            target_word = words[i]

            # Create highlighted version
            highlighted_context = escape(context).replace(
                escape(target_word), f'<span class="bg-warning">{escape(target_word)}</span>'
            )

            results.append(SearchResult(page_number=page.number, context=highlighted_context))

            if len(results) >= max_results:
                break

        i += 1

    return results


def render_results_table(results: List[SearchResult], has_more: bool) -> str:
    """Render search results as HTML table."""
    if not results:
        return '<p class="text-muted">No results found.</p>'

    rows = "\n".join(
        f"""
        <tr style="cursor: pointer;" 
            onclick="goToPage({result.page_number}, 0);
                    bootstrap.Modal.getInstance(document.getElementById('searchModal')).hide();">
            <td>{result.page_number}</td>
            <td>{result.context}</td>
        </tr>
        """
        for result in results
    )

    table = f"""
        <table class="table table-hover table-striped">
            <thead>
                <tr>
                    <th>Page</th>
                    <th>Context</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    """

    if has_more:
        table += """
            <div class="mt-2 text-center">
                <p class="text-muted">More results available...</p>
            </div>
        """

    return table


@smart_login_required
@require_POST  # type: ignore
def search(request: HttpRequest) -> HttpResponse:
    """Search for a term in the book."""
    book_code = request.POST.get("book-code")
    search_term = request.POST.get("searchInput", "").strip()
    whole_words = request.POST.get("whole-words") == "on"

    if not book_code:
        raise ValueError("Expected book-code")

    if len(search_term) < 3:
        return HttpResponse(render_results_table([], False))

    book = get_object_or_404(Book, code=book_code)
    book.ensure_can_be_read_by(request.user)

    pages = get_searchable_pages(book, search_term, MAX_SEARCH_RESULTS + 1)
    has_more = len(pages) > MAX_SEARCH_RESULTS

    results: List[SearchResult] = []
    for page in pages[:MAX_SEARCH_RESULTS]:
        page_results = find_matches_in_page(
            page, search_term, whole_words, MAX_SEARCH_RESULTS - len(results)
        )
        results.extend(page_results)
        if len(results) >= MAX_SEARCH_RESULTS:
            has_more = True
            break

    return HttpResponse(render_results_table(results, has_more))
