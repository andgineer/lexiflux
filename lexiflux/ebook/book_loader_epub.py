"""Import an EPUB file into the database."""

import logging
import os
import random
import re
from collections import defaultdict
from collections.abc import Iterable, Iterator
from typing import Any, Optional

from django.db import transaction
from ebooklib import ITEM_DOCUMENT, ITEM_IMAGE, epub
from lxml import etree
from pagesmith import parse_partial_html, refine_html
from pagesmith.html_page_splitter import HtmlPageSplitter

from lexiflux.ebook.book_loader_base import BookLoaderBase, MetadataField
from lexiflux.ebook.web_page_metadata import MetadataExtractor
from lexiflux.models import Book, BookImage

log = logging.getLogger()

MAX_ITEM_SIZE = 6000
PAGES_NUM_TO_DEBUG = 3


class BookLoaderEpub(BookLoaderBase):
    """Import ebook from EPUB.

    Save only forward links or backward links to <a> tags - we do not parse
    twice to collect internal links backward targets and place them into `keep_id`.
    """

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
        super().__init__(*args, **kwargs)

    @transaction.atomic  # type: ignore
    def create(self, owner_email: str, forced_language: Optional[str] = None) -> Book:
        """Save the book to the database."""
        book = super().create(owner_email, forced_language)

        # Save images to the database
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

    def load_text(self) -> None:
        self.epub = epub.read_epub(self.file_path)

    def detect_meta(self) -> tuple[dict[str, Any], int, int]:
        """Read the book and extract meta if it is present.

        Should set self.meta, self.start, self.end
        And return them in result (mostly for tests compatibility)
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

        self.meta = {
            MetadataField.TITLE: (
                self.epub.get_metadata("DC", "title")[0][0]
                if self.epub.get_metadata("DC", "title")
                else "Unknown Title"
            ),
        }
        authors = self.epub.get_metadata("DC", "creator")
        self.meta[MetadataField.AUTHOR] = authors[0][0] if authors else "Unknown Author"
        language_metadata = self.epub.get_metadata("DC", "language")
        self.meta[MetadataField.LANGUAGE] = (
            language_metadata[0][0] if language_metadata else self.detect_language()
        )
        self.book_start, self.book_end = 0, -1  # todo: detect start/finish of the book
        return self.meta, self.book_start, self.book_end

    def spine(self) -> Iterator[tuple[str, str, str, str]]:
        """Items in the EPUB spine."""
        for spine_id in self.epub.spine:
            item: epub.EpubItem = self.epub.get_item_with_id(spine_id[0])
            if item.get_type() == ITEM_DOCUMENT:
                log.debug(
                    "Processing spine: %s, name = %s, type = %s, id = %s, file_name = %s",
                    spine_id[0],
                    item.get_name(),
                    item.get_type(),
                    item.get_id(),
                    item.file_name,
                )
                yield (
                    item.get_body_content().decode("utf-8"),
                    item.file_name,
                    item.get_id(),
                    item.get_name(),
                )

    def pages(self) -> Iterator[str]:  ## noqa: C901,PLR0912  # todo: refactor
        """Split a text into pages of approximately equal length."""
        self.toc = []
        self.anchor_map = {}
        page_num = 1
        for content, item_filename, item_id, item_name in self.spine():  # pylint: disable=too-many-nested-blocks
            if page_num < PAGES_NUM_TO_DEBUG:
                log.debug(f"Content {item_filename}, page {page_num}:\n{content}")
            root = parse_partial_html(content)
            if len(content) > MAX_ITEM_SIZE:
                page_splitter = HtmlPageSplitter(
                    root=root,
                )
                for sub_page in page_splitter.pages():
                    page_root = parse_partial_html(sub_page)
                    if cleaned_content := self.clear_page(
                        root=page_root,
                        item_filename=item_filename,
                        item_id=item_id,
                        item_name=item_name,
                        page_num=page_num,
                    ):
                        yield cleaned_content
                        page_num += 1
            elif cleaned_content := self.clear_page(
                root=root,
                item_filename=item_filename,
                item_id=item_id,
                item_name=item_name,
                page_num=page_num,
            ):
                yield cleaned_content
                page_num += 1

        # Process TOC after all pages have been processed
        self._process_toc()

    def clear_page(  # noqa: PLR0913
        self,
        content: Optional[str] = None,
        root: Optional[etree._Element] = None,
        item_filename: str = "",
        item_id: str = "",
        item_name: str = "",
        page_num: int = 0,
    ) -> Optional[str]:
        if content is not None:
            root = parse_partial_html(content)
        self.keep_ids |= self.extract_ids_from_internal_links(root)
        cleaned_content = refine_html(root=root, ids_to_keep=self.keep_ids).strip()
        if page_num < PAGES_NUM_TO_DEBUG:
            log.debug(f"Cleaned {item_filename}, page {page_num}:\n{cleaned_content}")
        if cleaned_content:
            self._process_anchors(
                page_num,
                html_tree=root,
                file_name=item_filename,
                item_id=item_id,
                item_name=item_name,
            )
            return cleaned_content
        log.warning(f"Non-empty page cleaned to nothing: {item_filename}, page {page_num}")
        return None

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
                file_name = item.file_name
                result[file_name]["#"] = self.extract_title(item)
        log.debug("Generated TOC from spine: %s", result)
        return result

    def extract_title(self, item: epub.EpubItem) -> str:
        """Extract the title from the EPUB item."""
        extractor = MetadataExtractor(item.get_body_content().decode("utf-8"))
        return extractor.extract_part_title() or os.path.splitext(item.get_name())[0]

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
            cleaned_content = refine_html(content)

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
