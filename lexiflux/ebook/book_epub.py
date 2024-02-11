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

    def __init__(self, file_path: str, languages: Optional[List[str]] = None) -> None:
        """Initialize.

        file_path - a path to a file with EPUB.
        """
        self.languages = ["en", "sr"] if languages is None else languages
        self.epub = epub.read_epub(file_path)

        self.meta, self.book_start, self.book_end = self.detect_meta()
        self.meta[MetadataField.LANGUAGE] = self.get_language()
        self.headings = extract_toc(self.epub.toc)
        log.debug("Headings: %s", self.headings)

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
                yield item.get_body_content().decode("utf-8")

    def get_random_words(self, words_num: int = 15) -> str:
        """Get random words from the book."""
        raise NotImplementedError  # todo: implement


def extract_toc(toc: List[Any]) -> List[Any]:
    """Extract the table of contents from an EPUB.

    :param toc: A list representing the table of contents.
    :return: A list containing the structured table of contents.
    """
    print(f"Extracting TOC: {toc}")
    result: List[Any] = []

    if isinstance(toc, Iterable):
        for item_idx, item in enumerate(toc):
            if isinstance(item, tuple) and len(item) == 2:
                result.append({item[0].title: extract_toc(item[1])})
            elif isinstance(item, Iterable):
                result.append(extract_toc(list(item)))
            elif isinstance(item, epub.Link):
                result.append({item.title: item.href})
            elif isinstance(item, epub.Section):
                result.append({item.title: extract_toc(toc[item_idx + 1 :])})
                item_idx += 1

    return result
