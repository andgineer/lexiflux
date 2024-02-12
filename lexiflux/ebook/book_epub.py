"""Import an EPUB file into the database."""
import logging
from typing import Any, Iterable, List, Optional, Tuple, Dict, Iterator

from ebooklib import ITEM_DOCUMENT, epub

from lexiflux.ebook.book_base import BookBase, MetadataField


log = logging.getLogger()


class BookEpub(BookBase):
    """Import ebook from EPUB."""

    book_start: int
    book_end: int
    heading_hrefs: Dict[str, str]  # map hrefs to headings

    def __init__(self, file_path: str, languages: Optional[List[str]] = None) -> None:
        """Initialize.

        file_path - a path to a file with EPUB.
        """
        self.languages = ["en", "sr"] if languages is None else languages
        self.epub = epub.read_epub(file_path)

        self.meta, self.book_start, self.book_end = self.detect_meta()
        self.meta[MetadataField.LANGUAGE] = self.get_language()
        self.heading_hrefs = {  # reverse href/title in flatten epub headings
            value: key
            for heading in flatten_list(extract_headings(self.epub.toc))
            for key, value in heading.items()
        }
        log.debug("Extracted epub headings: %s", self.heading_hrefs)

    def detect_meta(self) -> Tuple[Dict[str, Any], int, int]:
        """Try to detect book meta and text.

        Extract meta if it is present.
        Trim meta text from the beginning and end of the book text.
        Return: meta, start, end
        """
        meta = {}
        meta[MetadataField.TITLE] = (
            self.epub.get_metadata("DC", "title")[0][0]
            if self.epub.get_metadata("DC", "title")
            else "Unknown Title"
        )
        authors = self.epub.get_metadata("DC", "creator")
        meta[MetadataField.AUTHOR] = authors[0][0] if authors else "Unknown Author"
        language_metadata = self.epub.get_metadata("DC", "language")
        meta[MetadataField.LANGUAGE] = (
            language_metadata[0][0] if language_metadata else self.get_language()
        )
        return meta, 0, -1  #  todo: detect start/finish of the book

    def pages(self) -> Iterator[str]:
        """Split a text into pages of approximately equal length.

        Also clear headings and recollect them during pages generation.
        """
        self.toc = []
        for spine_id in self.epub.spine:
            item: epub.EpubItem = self.epub.get_item_with_id(spine_id[0])
            # todo: if we found anchor or item for the heading from self.heading_hrefs,
            #  add it to the toc and remove from self.heading_hrefs
            # It will be sorted automatically as we scan pages from beginning to end
            # May be start with item match and then try to find anchor and fix the entry?
            if item.get_type() == ITEM_DOCUMENT:
                log.debug(
                    "Processing page: %s, name = %s, type = %s, id = %s, file_name = %s",
                    spine_id[0],
                    item.get_name(),
                    item.get_type(),
                    item.get_id(),
                    item.file_name,
                )
                yield item.get_body_content().decode("utf-8")
        # todo: for items left in self.heading_hrefs, do something intelligent?

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
