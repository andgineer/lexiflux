"""Import an EPUB file into the database."""

import logging
import os
import random
import re
from collections import defaultdict
from typing import Any, Iterable, List, Optional, Tuple, Dict, Iterator

from bs4 import BeautifulSoup, Tag, NavigableString
from django.db import transaction
from ebooklib import ITEM_DOCUMENT, epub, ITEM_IMAGE

from lexiflux.ebook.book_loader_base import BookLoaderBase, MetadataField
from lexiflux.models import BookImage, Book

log = logging.getLogger()

MAX_ITEM_SIZE = 6000
TARGET_PAGE_SIZE = 3000

PAGES_NUM_TO_DEBUG = 10  # number of page for detailed tracing


class BookLoaderEpub(BookLoaderBase):
    """Import ebook from EPUB."""

    book_start: int
    book_end: int
    heading_hrefs: Dict[str, Dict[str, str]]

    WORD_ESTIMATED_LENGTH = 30
    MIN_RANDOM_WORDS = 3
    JUNK_TEXT_BEGIN_PERCENT = 5
    JUNK_TEXT_END_PERCENT = 5
    MAX_RANDOM_WORDS_ATTEMPTS = 10  # Maximum number of attempts to find a suitable page

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.anchor_map: Dict[str, Dict[str, Any]] = {}

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

    def detect_meta(self) -> Tuple[Dict[str, Any], int, int]:
        """Read the book and extract meta if it is present.

        Return: meta, start, end
        """
        self.epub = epub.read_epub(self.file_path)

        self.heading_hrefs = href_hierarchy(
            {  # reverse href/title in flatten epub headings
                value: key
                for heading in flatten_list(extract_headings(self.epub.toc))
                for key, value in heading.items()
            }
        )
        log.debug("Extracted epub headings: %s", self.heading_hrefs)

        meta = {
            MetadataField.TITLE: (
                self.epub.get_metadata("DC", "title")[0][0]
                if self.epub.get_metadata("DC", "title")
                else "Unknown Title"
            )
        }
        authors = self.epub.get_metadata("DC", "creator")
        meta[MetadataField.AUTHOR] = authors[0][0] if authors else "Unknown Author"
        language_metadata = self.epub.get_metadata("DC", "language")
        meta[MetadataField.LANGUAGE] = (
            language_metadata[0][0] if language_metadata else self.get_language()
        )
        return meta, 0, -1  # todo: detect start/finish of the book

    def pages(self) -> Iterator[str]:  # pylint: disable=too-many-branches
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
                    for sub_page in self._split_content(soup):
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
                                    f"Empty page generated for {item.file_name}, page {page_num}"
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

    def _split_content(self, soup: BeautifulSoup) -> Iterator[str]:
        """Split content into pages using recursive tag handling."""
        contents = soup.body.contents if soup.body else soup.contents
        yield from self._split_elements(contents)

    def _split_elements(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        self, elements: List[Any], current_size: int = 0, current_chunk: Optional[List[str]] = None
    ) -> Iterator[str]:
        """Recursively split elements into chunks of appropriate size.

        Args:
            elements: List of BeautifulSoup elements to process
            current_size: Running total of current chunk size
            current_chunk: Accumulated content for current page
        """
        if current_chunk is None:
            current_chunk = []

        for element in elements:  # pylint: disable=too-many-nested-blocks
            if isinstance(element, NavigableString):
                # Handle text content
                text = str(element).strip()
                if not text:
                    continue

                sentences = re.split(r"([.!?。？！]+\s*)", text)

                for i in range(0, len(sentences), 2):
                    sentence = sentences[i]
                    punctuation = sentences[i + 1] if i + 1 < len(sentences) else ""

                    complete_sentence = sentence + (punctuation or "")
                    sentence_size = len(complete_sentence)

                    if current_size + sentence_size <= TARGET_PAGE_SIZE:
                        current_chunk.append(complete_sentence)
                        current_size += sentence_size
                    else:
                        if current_chunk:
                            yield "".join(current_chunk)
                            current_chunk.clear()
                            current_size = 0

                        # Handle sentences larger than target size
                        if sentence_size > TARGET_PAGE_SIZE:
                            words = complete_sentence.split()
                            temp: List[str] = []
                            temp_size = 0

                            for word in words:
                                word_size = len(word) + 1  # +1 for space
                                if temp_size + word_size > TARGET_PAGE_SIZE and temp:
                                    yield " ".join(temp)
                                    temp = []
                                    temp_size = 0
                                temp.append(word)
                                temp_size += word_size

                            if temp:
                                current_chunk.append(" ".join(temp))
                                current_size = temp_size
                        else:
                            current_chunk.append(complete_sentence)
                            current_size = sentence_size

            elif isinstance(element, Tag):
                # Convert tag to string to get its complete HTML representation
                tag_html = str(element)
                tag_size = len(tag_html)

                # If the entire tag is small enough, keep it together
                if tag_size <= TARGET_PAGE_SIZE * 1.5:  # Allow slightly larger for complete tags
                    if current_size + tag_size > TARGET_PAGE_SIZE and current_chunk:
                        yield "".join(current_chunk)
                        current_chunk.clear()
                        current_size = 0
                    current_chunk.append(tag_html)
                    current_size += tag_size
                else:
                    # split large tags while preserving tag structure
                    attrs_str = " ".join(f'{k}="{v}"' for k, v in element.attrs.items())
                    space = " " if element.attrs else ""
                    opening_tag = f"<{element.name}{space}{attrs_str}>"

                    closing_tag = f"</{element.name}>"

                    # If current chunk exists and adding opening tag would exceed size, yield it
                    if current_chunk and current_size + len(opening_tag) > TARGET_PAGE_SIZE:
                        yield "".join(current_chunk)
                        current_chunk.clear()
                        current_size = 0

                    # Add opening tag to new chunk
                    current_chunk.append(opening_tag)
                    current_size += len(opening_tag)

                    # Process contents
                    if element.contents:
                        for content in self._split_elements(element.contents):
                            if current_size + len(content) + len(closing_tag) <= TARGET_PAGE_SIZE:
                                current_chunk.append(content)
                                current_size += len(content)
                            else:
                                # End current chunk with closing tag
                                current_chunk.append(closing_tag)
                                yield "".join(current_chunk)
                                # Start new chunk with opening tag
                                current_chunk = [opening_tag, content]
                                current_size = len(opening_tag) + len(content)

                    # Add closing tag to last chunk
                    current_chunk.append(closing_tag)
                    current_size += len(closing_tag)

        # Yield any remaining content
        if current_chunk:
            yield "".join(current_chunk)

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

    def _process_anchors(self, item: epub.EpubItem, current_page: int, content: str) -> None:
        """Process anchors for a page."""
        soup = BeautifulSoup(content, "html.parser")
        for anchor in soup.find_all(lambda tag: tag.has_attr("id")):
            anchor_id = anchor["id"]
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
            random_item = random.choice(document_items)
            content = random_item.get_body_content().decode("utf-8")

            # Clean the content
            cleaned_content = clear_html(content)

            expected_length = self.WORD_ESTIMATED_LENGTH * words_num * 2

            if len(cleaned_content) < expected_length:
                # For short documents, use the full content
                fragment = cleaned_content
            else:
                # For longer documents, select a random starting point
                start = random.randint(0, len(cleaned_content) - expected_length)
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


def extract_headings(epub_toc: List[Any]) -> List[Dict[str, Any]]:
    """Extract headings from an EPUB.

    :param epub_toc: A toc from epub object.
    :return: A list of {"title": "href" | nested headings}.
    """
    log.debug("Extracting epub Headings from: %s", epub_toc)
    result: List[Any] = []

    if isinstance(epub_toc, Iterable):
        for item_idx, item in enumerate(epub_toc):
            if isinstance(item, tuple) and len(item) == 2:
                result.append({item[0].title: extract_headings(item[1])})
            elif isinstance(item, Iterable):
                result.append(extract_headings(list(item)))
            elif isinstance(item, epub.Link):
                result.append({item.title: item.href})
            elif isinstance(item, epub.Section):
                result.append({item.title: extract_headings(epub_toc[item_idx + 1 :])})
                item_idx += 1

    return result


def flatten_list(
    data: List[Dict[str, Any]], parent_key: str = "", sep: str = "."
) -> List[Dict[str, Any]]:
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


def href_hierarchy(input_dict: Dict[str, str]) -> Dict[str, Dict[str, str]]:
    """Convert a flat TOC hrefs to a hierarchy.

    result: {"epub item file name": {"": "title", "#anchor-inside-the-file": "sub_title" ...}, ...}
    """
    result: Dict[str, Dict[str, str]] = defaultdict(dict)
    for key, value in input_dict.items():
        parts = key.split("#")
        page = parts[0]
        anchor = f"#{parts[1]}" if len(parts) > 1 else "#"
        result[page][anchor] = value
    return result


def clear_html(  # pylint: disable=too-many-positional-arguments,too-many-arguments
    input_html: str,
    tags_to_remove_with_content: Iterable[str] = ("head", "style", "script", "svg", "noscript"),
    tags_to_remove_keeping_content: Iterable[str] = ("body", "html"),
    tags_to_clear_attributes: Iterable[str] = ("p", "br"),
    tag_to_partially_clear_attributes: Dict[str, List[str]] | None = None,
    heading_classes: Dict[str, str] | None = None,
) -> str:
    """Clean HTML from tags and attributes and add classes to heading tags."""
    if tag_to_partially_clear_attributes is None:
        tag_to_partially_clear_attributes = {
            "img": ["src", "alt", "style"],
            "span": ["id"],
            "div": ["id"],
            "h1": ["id"],
            "h2": ["id"],
            "h3": ["id"],
            "h4": ["id"],
            "h5": ["id"],
        }

    if heading_classes is None:
        heading_classes = {
            "h1": "display-4 fw-semibold text-primary mb-4",
            "h2": "display-5 fw-semibold text-secondary mb-3",
            "h3": "h3 fw-normal text-dark mb-3",
            "h4": "h4 fw-normal text-dark mb-2",
            "h5": "h5 fw-normal text-dark mb-2",
        }

    try:
        soup = BeautifulSoup(input_html, "html.parser")
        for tag in tags_to_remove_with_content:
            for match in soup.find_all(tag):
                match.decompose()
        for tag in tags_to_remove_keeping_content:
            for match in soup.find_all(tag):
                match.unwrap()
        for tag in soup.find_all(tags_to_clear_attributes):
            tag.attrs = {}  # type: ignore
        for tag, attrs in tag_to_partially_clear_attributes.items():
            for match in soup.find_all(tag):
                match.attrs = {
                    attr: match.attrs.get(attr, "") for attr in attrs if attr in match.attrs
                }

        # Add classes to heading tags
        for tag, classes in heading_classes.items():
            for match in soup.find_all(tag):
                match["class"] = match.get("class", []) + classes.split()

        return str(soup)
    except Exception as e:  # pylint: disable=broad-except
        log.error("Error cleaning HTML: %s", e)
        return input_html
