"""Import an EPUB file into the database."""

import logging
import os
import random
import re
from collections import defaultdict
from collections.abc import Iterable, Iterator
from typing import Any, Optional

from bs4 import BeautifulSoup, Tag
from django.db import transaction
from ebooklib import ITEM_DOCUMENT, ITEM_IMAGE, epub

from lexiflux.ebook.book_loader_base import BookLoaderBase, MetadataField
from lexiflux.ebook.clear_html import clear_html
from lexiflux.ebook.html_page_splitter import HtmlPageSplitter
from lexiflux.models import Book, BookImage

log = logging.getLogger()

MAX_ITEM_SIZE = 6000
TARGET_PAGE_SIZE = 3000

PAGES_NUM_TO_DEBUG = 3  # number of page for detailed tracing


class BookLoaderEpub(BookLoaderBase):
    """Import ebook from EPUB."""

    epub: Any
    book_start: int
    book_end: int
    heading_hrefs: dict[str, dict[str, str]]

    WORD_ESTIMATED_LENGTH = 30
    MIN_RANDOM_WORDS = 3
    JUNK_TEXT_BEGIN_PERCENT = 5
    JUNK_TEXT_END_PERCENT = 5
    MAX_RANDOM_WORDS_ATTEMPTS = 10  # Maximum number of attempts to find a suitable page

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.page_splitter = HtmlPageSplitter(target_page_size=TARGET_PAGE_SIZE)
        super().__init__(*args, **kwargs)
        self.anchor_map: dict[str, dict[str, Any]] = {}

    @transaction.atomic  # type: ignore
    def create(self, owner_email: str, forced_language: Optional[str] = None) -> Book:
        """Save the book to the database."""
        book = super().create(owner_email, forced_language)
        book.anchor_map = self.anchor_map
        for item in self.epub.get_items():
            if item.get_type() == ITEM_IMAGE:
                # If Windows path, replace backslashes with slashes
                normalized_filename = os.path.normpath(item.get_name()).replace("\\", "/")
                if item.file_name != item.get_name():
                    log.warning(
                        "EPUB image file_name (%s) != get_name() (%s)",
                        item.file_name,
                        item.get_name(),
                    )
                BookImage.objects.create(
                    book=book,
                    image_data=item.get_content(),
                    content_type=item.media_type,
                    filename=normalized_filename,
                )
        return book

    def load_text(self) -> str:
        self.epub = epub.read_epub(self.file_path)
        return ""

    def detect_meta(self) -> tuple[dict[str, Any], int, int]:
        """Read the book and extract meta if it is present.

        Return: meta, start, end
        """

        self.heading_hrefs = {}
        if self.epub.toc:
            self.heading_hrefs = href_hierarchy(
                {  # reverse href/title in flatten epub headings
                    value: key
                    for heading in flatten_list(extract_headings(self.epub.toc))
                    for key, value in heading.items()
                },
            )
            log.debug("Extracted epub headings: %s", self.heading_hrefs)
        if not self.heading_hrefs:
            log.warning("No TOC found in EPUB. Generating TOC from spine.")
            self.heading_hrefs = self.generate_toc_from_spine()

        meta = {
            MetadataField.TITLE: (
                self.epub.get_metadata("DC", "title")[0][0]
                if self.epub.get_metadata("DC", "title")
                else "Unknown Title"
            ),
        }
        authors = self.epub.get_metadata("DC", "creator")
        meta[MetadataField.AUTHOR] = authors[0][0] if authors else "Unknown Author"
        language_metadata = self.epub.get_metadata("DC", "language")
        meta[MetadataField.LANGUAGE] = (
            language_metadata[0][0] if language_metadata else self.detect_language()
        )
        return meta, 0, -1  # todo: detect start/finish of the book

    def pages(self) -> Iterator[str]:  ## noqa: C901,PLR0912  # todo: refactor
        """Split a text into pages of approximately equal length."""
        self.toc = []
        page_num = 1
        for spine_id in self.epub.spine:  # pylint: disable=too-many-nested-blocks
            item: epub.EpubItem = self.epub.get_item_with_id(spine_id[0])
            if item.get_type() == ITEM_DOCUMENT:
                log.debug(
                    "Processing page: %s, name = %s, type = %s, id = %s, file_name = %s",
                    spine_id[0],
                    item.get_name(),
                    item.get_type(),
                    item.get_id(),
                    item.file_name,
                )
                soup = BeautifulSoup(item.get_body_content().decode("utf-8"), "html.parser")
                content = str(soup)
                if page_num < PAGES_NUM_TO_DEBUG:
                    log.debug(f"Content: {content}")
                if len(content) > MAX_ITEM_SIZE:
                    for sub_page in self.page_splitter.split_content(soup):
                        if sub_page.strip():  # Only process non-empty pages
                            sub_soup = BeautifulSoup(sub_page, "html.parser")
                            cleaned_content = clear_html(str(sub_soup)).strip()
                            if cleaned_content:
                                self._process_anchors(item, page_num, cleaned_content)
                                if page_num < PAGES_NUM_TO_DEBUG:
                                    log.debug(f"SubPage {page_num}: {cleaned_content}")
                                yield cleaned_content
                                page_num += 1
                            else:
                                log.warning(
                                    f"Empty page generated for {item.file_name}, page {page_num}",
                                )
                        else:
                            log.warning(f"Empty sub-page skipped for {item.file_name}")
                else:
                    cleaned_content = clear_html(content).strip()
                    if cleaned_content:
                        self._process_anchors(item, page_num, cleaned_content)
                        if page_num < PAGES_NUM_TO_DEBUG:
                            log.debug(f"Page {page_num}: {cleaned_content}")
                        yield cleaned_content
                        page_num += 1
                    else:
                        log.warning(f"Empty page skipped for {item.file_name}")

        # Process TOC after all pages have been processed
        self._process_toc()

    def _process_toc(self) -> None:
        """Process table of contents using the anchor_map."""
        for file_name, anchors in self.heading_hrefs.items():
            for anchor, title in anchors.items():
                full_anchor = f"{file_name}{anchor}"
                if full_anchor in self.anchor_map:
                    page_num = self.anchor_map[full_anchor]["page"]
                    self.toc.append((title, page_num, 0))
                elif file_name in self.anchor_map and anchor == "#":
                    # Handle the case where the anchor is for the start of the file
                    page_num = self.anchor_map[file_name]["page"]
                    self.toc.append((title, page_num, 0))

    def generate_toc_from_spine(self) -> dict[str, dict[str, str]]:
        """Generate TOC from the EPUB spine when no TOC is present."""
        result: dict[str, dict[str, str]] = defaultdict(dict)
        for spine_id in self.epub.spine:
            item: epub.EpubItem = self.epub.get_item_with_id(spine_id[0])
            log.debug(f"Spine item: {item.get_name()}")
            if item.get_type() == ITEM_DOCUMENT:
                # Extract title from the document's metadata or content
                title = self.extract_title(item) or os.path.splitext(item.get_name())[0]
                file_name = item.file_name
                result[file_name]["#"] = title
        log.debug("Generated TOC from spine: %s", result)
        return result

    def extract_title(self, item: epub.EpubItem) -> Optional[str]:
        """Extract the title from the EPUB item."""
        try:
            soup = BeautifulSoup(item.get_body_content().decode("utf-8"), "html.parser")

            # Prioritize standard <title> tag in the <head>
            title_tag = soup.find("title")
            if title_tag and title_tag.get_text(strip=True):
                log.debug(
                    "Extracted title from <title> tag in item %s: %s",
                    item.get_id(),
                    title_tag.get_text(separator=" ", strip=True),
                )
                return title_tag.get_text(separator=" ", strip=True)  # type: ignore

            # Search for common heading tags in the body
            for heading in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                heading_tag = soup.find(heading)
                if heading_tag and heading_tag.get_text(strip=True):
                    log.debug(
                        "Extracted title from <%s> tag in item %s: %s",
                        heading,
                        item.get_id(),
                        heading_tag.get_text(separator=" ", strip=True),
                    )
                    return heading_tag.get_text(separator=" ", strip=True)  # type: ignore

            # Check for other common patterns that might indicate a title
            potential_titles = soup.find_all(attrs={"class": re.compile(r"title", re.IGNORECASE)})
            for tag in potential_titles:
                if tag.get_text(strip=True):
                    log.debug(
                        "Extracted title from class 'title' in item %s: %s",
                        item.get_id(),
                        tag.get_text(separator=" ", strip=True),
                    )
                    return tag.get_text(separator=" ", strip=True)  # type: ignore

            log.warning("No title found for item %s", item.get_id())
        except Exception as e:  # noqa: BLE001
            log.error("Error extracting title from item %s: %s", item.get_id(), e)
        return None

    def _process_anchors(self, item: epub.EpubItem, current_page: int, content: str) -> None:
        """Process anchors for a page."""
        soup = BeautifulSoup(content, "html.parser")
        for anchor in soup.find_all(lambda tag: tag.has_attr("id")):
            if isinstance(anchor, Tag):
                anchor_id = str(anchor["id"])
                self.anchor_map[f"{item.file_name}#{anchor_id}"] = {
                    "page": current_page,
                    "item_id": item.get_id(),
                    "item_name": item.get_name(),
                }

        # Add an entry for the start of the document if it hasn't been added yet
        if item.file_name not in self.anchor_map:
            self.anchor_map[item.file_name] = {
                "page": current_page,
                "item_id": item.get_id(),
                "item_name": item.get_name(),
            }

    def get_random_words(self, words_num: int = 15) -> str:
        """Get random words from the book."""
        document_items = [
            item for item in self.epub.get_items() if item.get_type() == ITEM_DOCUMENT
        ]

        if not document_items:
            return ""

        words = []
        for _ in range(self.MAX_RANDOM_WORDS_ATTEMPTS):
            random_item = random.choice(document_items)  # noqa: S311
            content = random_item.get_body_content().decode("utf-8")

            # Clean the content
            cleaned_content = clear_html(content)

            expected_length = self.WORD_ESTIMATED_LENGTH * words_num * 2

            if len(cleaned_content) < expected_length:
                # For short documents, use the full content
                fragment = cleaned_content
            else:
                # For longer documents, select a random starting point
                start = random.randint(0, len(cleaned_content) - expected_length)  # noqa: S311
                fragment = cleaned_content[start : start + expected_length]

            # Split into words, skipping the first word in case it's partial
            words = re.split(r"\s+", fragment)[1 : words_num + 1]

            # Skip documents that are too short
            if len(cleaned_content) < self.WORD_ESTIMATED_LENGTH * words_num * 2:
                continue

            if len(words) >= self.MIN_RANDOM_WORDS:
                return " ".join(words)

        # If we couldn't find suitable words after MAX_ATTEMPTS, return whatever we have
        return " ".join(words) if words else ""


def extract_headings(epub_toc: list[Any]) -> list[dict[str, Any]]:
    """Extract headings from an EPUB.

    :param epub_toc: A toc from epub object.
    :return: A list of {"title": "href" | nested headings}.
    """
    log.debug("Extracting epub Headings from: %s", epub_toc)
    result: list[Any] = []

    if isinstance(epub_toc, Iterable):
        for item_idx, item in enumerate(epub_toc):
            if isinstance(item, tuple) and len(item) == 2:  # noqa: PLR2004
                result.append({item[0].title: extract_headings(item[1])})
            elif isinstance(item, Iterable):
                result.append(extract_headings(list(item)))
            elif isinstance(item, epub.Link):
                result.append({item.title: item.href})
            elif isinstance(item, epub.Section):
                result.append({item.title: extract_headings(epub_toc[item_idx + 1 :])})
                item_idx += 1  # noqa: PLW2901

    return result


def flatten_list(
    data: list[dict[str, Any]],
    parent_key: str = "",
    sep: str = ".",
) -> list[dict[str, Any]]:
    """Flatten a list of dictionaries."""
    items = []
    for item in data:
        for key, value in item.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            if isinstance(value, list):
                items.extend(flatten_list(value, new_key, sep=sep))
            else:
                items.append({new_key: value})
    return items


def href_hierarchy(input_dict: dict[str, str]) -> dict[str, dict[str, str]]:
    """Convert a flat TOC hrefs to a hierarchy.

    result: {"epub item file name": {"": "title", "#anchor-inside-the-file": "sub_title" ...}, ...}
    """
    result: dict[str, dict[str, str]] = defaultdict(dict)
    for key, value in input_dict.items():
        parts = key.split("#")
        page = parts[0]
        anchor = f"#{parts[1]}" if len(parts) > 1 else "#"
        result[page][anchor] = value
    return result
