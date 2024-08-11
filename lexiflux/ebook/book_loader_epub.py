"""Import an EPUB file into the database."""

import logging
from collections import defaultdict
from typing import Any, Iterable, List, Optional, Tuple, Dict, Iterator

from bs4 import BeautifulSoup
from ebooklib import ITEM_DOCUMENT, epub, ITEM_IMAGE

from lexiflux.ebook.book_loader_base import BookLoaderBase, MetadataField
from lexiflux.models import BookImage, Book

log = logging.getLogger()


class BookLoaderEpub(BookLoaderBase):
    """Import ebook from EPUB."""

    book_start: int
    book_end: int
    heading_hrefs: Dict[str, Dict[str, str]]

    def create(self, owner_email: str, forced_language: Optional[str] = None) -> Book:
        """Save the book to the database."""
        book = super().create(owner_email, forced_language)
        for item in self.epub.get_items():
            if item.get_type() == ITEM_IMAGE:
                BookImage.objects.create(
                    book=book,
                    image_data=item.get_content(),
                    content_type=item.media_type,
                    filename=item.get_name(),
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

    def pages(self) -> Iterator[str]:
        """Split a text into pages of approximately equal length.

        Also clear headings and recollect them during pages generation.
        """
        self.toc = []
        page_num = 0
        content_accumulator = ""
        for spine_id in self.epub.spine:
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
                # todo: split epub item to pages
                page_num += 1
                content_accumulator += (
                    f"{content_accumulator} "
                    + clear_html(item.get_body_content().decode("utf-8")).strip()
                )
                if item.file_name in self.heading_hrefs:
                    header_anchors = self.heading_hrefs[item.file_name]
                    if "#" in header_anchors:
                        self.toc.append((header_anchors["#"], page_num, 0))
                if len(content_accumulator) > 1000:
                    yield content_accumulator
                    content_accumulator = ""
                # todo: detect headings inside pages text and store them in self._detected_toc
        #  set self._detected_toc as TOC if epab.toc too small

    def get_random_words(self, words_num: int = 15) -> str:
        """Get random words from the book."""
        raise NotImplementedError  # todo: implement


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


def clear_html(  # pylint: disable=dangerous-default-value  # we do not modify it
    input_html: str,
    tags_to_remove_with_content: Iterable[str] = ("head", "style", "script", "svg", "noscript"),
    tags_to_remove_keeping_content: Iterable[str] = ("body", "html", "span", "div"),
    tags_to_clear_attributes: Iterable[str] = ("p", "br", "h1", "h2", "h3", "h4", "h5", "h6"),
    tag_to_partially_clear_attributes: Dict[str, List[str]] = {"img": ["src", "alt", "style"]},
) -> str:
    """Clean HTML from tags and attributes."""
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
        for tag in tag_to_partially_clear_attributes:
            for match in soup.find_all(tag):
                match.attrs = {
                    attr: match.attrs.get(attr, "")
                    for attr in tag_to_partially_clear_attributes[tag]
                }

        return str(soup)
    except Exception as e:  # pylint: disable=broad-except
        log.error("Error cleaning HTML: %s", e)
        return input_html
