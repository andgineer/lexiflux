"""Import ebook from HTML."""

import logging
from collections.abc import Iterator

from pagesmith import parse_partial_html
from pagesmith.html_page_splitter import HtmlPageSplitter

from lexiflux.ebook.book_loader_plain_text import BookLoaderPlainText

PAGES_NUM_TO_DEBUG = 3

log = logging.getLogger(__name__)


class BookLoaderHtml(BookLoaderPlainText):
    """Import ebook from HTML."""

    escape_html = False

    def load_text(self) -> None:
        super().load_text()
        self.tree_root = parse_partial_html(self.text)

    def pages(self) -> Iterator[str]:
        """Split a text into pages of approximately equal length.

        Also clear headings and recollect them during pages generation.
        """
        page_splitter = HtmlPageSplitter(
            root=self.tree_root,
        )
        for page_num, page_html in enumerate(page_splitter.pages(), start=1):
            if page_html.strip():  # Only process non-empty pages
                if page_num < PAGES_NUM_TO_DEBUG:
                    log.debug(f"Page {page_num}: {page_html}")
                self._process_anchors(
                    page_num,
                    page_html,
                )
                if page_num < PAGES_NUM_TO_DEBUG:
                    log.debug(f"Page {page_num}: {page_html}")
                yield page_html
