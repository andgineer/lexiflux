"""Import a plain text file into Lexiflux."""

import logging
import random
import re
from collections.abc import Iterator
from html import escape
from typing import Any

from chardet.universaldetector import UniversalDetector
from pagesmith import ChapterDetector, PageSplitter

from lexiflux.ebook.book_loader_base import BookLoaderBase, MetadataField
from lexiflux.models import Book, BookPage

log = logging.getLogger()


class BookLoaderPlainText(BookLoaderBase):  # pylint: disable=too-many-instance-attributes
    """Import ebook from plain text."""

    escape_html = True

    CHAPTER_HEADER_DISTANCE = 300  # Minimum character distance between chapter headers
    GUTENBERG_ENDING_SIZE = 30 * 1024  # Maximum size of the Gutenberg licence text
    GUTENBERG_START_SIZE = 1024  # Minimum size of the Gutenberg preamble
    JUNK_TEXT_BEGIN_PERCENT = 5
    JUNK_TEXT_END_PERCENT = 5
    ONE_HUNDRED_PERCENT = 100
    assert JUNK_TEXT_END_PERCENT + JUNK_TEXT_BEGIN_PERCENT < ONE_HUNDRED_PERCENT
    WORD_ESTIMATED_LENGTH = 30
    MIN_RANDOM_WORDS = 3

    book_start: int
    book_end: int

    def load_text(self) -> None:
        if isinstance(self.file_path, str):
            self.text = self.read_file(self.file_path)
        else:
            self.text = self.file_path.read()

    def detect_meta(self) -> tuple[dict[str, Any], int, int]:
        """Try to detect book meta and text.

        Extract meta if it is present.
        Trim meta text from the beginning and end of the book text.

        Should set self.meta, self.start, self.end
        And return them in result (mostly for tests compatibility)
        """
        self.meta, self.book_start = self.parse_gutenberg_header()
        self.book_end = self.cut_gutenberg_ending()
        if self.book_start > self.book_end:
            self.book_start = 0
            self.book_end = len(self.text)
        return self.meta, self.book_start, self.book_end

    def read_file(self, file_path: str) -> str:
        """Read file with detecting correct encoding."""
        detector = UniversalDetector()
        with open(file_path, "rb") as file:
            for line in file:
                detector.feed(line)
                if detector.done:
                    break
        detector.close()
        log.debug("CharDet: %s", detector.result)
        encoding = detector.result["encoding"]

        with open(file_path, encoding=encoding) as f:
            return f.read()

    def get_random_words(self, words_num: int = 15) -> str:
        """Get random words from the book."""
        expected_words_length = self.WORD_ESTIMATED_LENGTH * words_num * 2
        start_index = int(len(self.text) * self.JUNK_TEXT_BEGIN_PERCENT / 100) + self.book_start
        end_index = (
            int(
                self.book_start
                + (self.book_end - self.book_start) * (100 - self.JUNK_TEXT_END_PERCENT) / 100,
            )
            - expected_words_length
        )
        if end_index <= self.book_start:
            end_index = self.book_end

        start = random.randint(start_index, max(start_index, end_index))  # noqa: S311
        log.debug("Random words start: %s, [%s, %s]", start, start_index, end_index)
        fragment = self.text[start : start + expected_words_length]
        # Skip the first word in case it's partially cut off
        words = re.split(r"\s", fragment)[1 : words_num + 1]
        if len(words) < words_num and len(words) < self.MIN_RANDOM_WORDS:
            # probably not a text so just return string
            words = [fragment[: self.WORD_ESTIMATED_LENGTH * words_num]]
        return " ".join(words)

    def normalize(self, text: str) -> str:
        """Make later processing more simple."""
        if self.escape_html:
            text = escape(text)
            # todo: remove <br/> from the start of the page
        text = re.sub(r"(\r?\n|\u2028|\u2029)", " <br/> ", text)
        return re.sub(r"[ \t]+", " ", self.fix_coding(text))

    def fix_coding(self, text: str) -> str:
        """Fix common coding issues in serbian books."""
        if self.meta[MetadataField.LANGUAGE].lower() in ["serbian", "croatian", "bosnian"]:
            text = text.replace("ţ", "ž")
            text = text.replace("Ď", "đ")
            text = text.replace("ĉ", "č")
            text = text.replace("Ĉ", "Č")
            text = text.replace("Ċ", "đ")
        return text

    def pages(self) -> Iterator[str]:
        """Split a text into pages of approximately equal length.

        Also clear headings and recollect them during pages generation.
        """
        page_splitter = PageSplitter(self.text, start=self.book_start, end=self.book_end)
        for page in page_splitter.pages():
            yield self.normalize(page)

    def create_page(self, book_instance: Book, page_num: int, page_content: str) -> BookPage:
        page = super().create_page(book_instance, page_num, page_content)
        if self.escape_html:  # Only for plain text book
            chapter_detector = ChapterDetector()
            if chapters := chapter_detector.get_chapters(page_content, page_num):
                toc_entries = [
                    (
                        chapter.title,
                        page_num,
                        page.find_word_at_position(chapter.position),
                    )
                    for chapter in chapters
                ]
                self.toc.extend(toc_entries)
        return page

    def cut_gutenberg_ending(self) -> int:
        """For books from Project Gutenberg cut off licence."""
        end_patterns = [
            "End of the Project Gutenberg EBook",
            "End of Project Gutenberg's",
            "*** END OF THE PROJECT GUTENBERG EBOOK",
            "*** END OF THIS PROJECT GUTENBERG EBOOK",
        ]
        for pattern in end_patterns:
            index = self.text.find(pattern, min(0, len(self.text) - self.GUTENBERG_ENDING_SIZE))
            if index != -1:
                return index
        return len(self.text)

    def parse_gutenberg_header(self) -> tuple[dict[str, Any], int]:
        """For books from Project Gutenberg cut off licence and extract meta.

        Return meta, header_end.
        """
        header = self.text[: self.GUTENBERG_START_SIZE]
        header_signature_pattern = r"^[\uFEFF\s]*The Project Gutenberg eBook"
        header_patterns = {
            MetadataField.TITLE: r"Title:\s*([^\n]*)\n",
            MetadataField.AUTHOR: r"Author:\s*([^\n]*)\n",
            MetadataField.RELEASED: r"Release date:\s*([^\n]*)\n",
            MetadataField.LANGUAGE: r"Language:\s*([^\n]*)\n",
            MetadataField.CREDITS: r"Credits:\s*([^\n]*)\n",
        }
        if signature := re.search(header_signature_pattern, header):
            meta = {}
            header_end_pattern = r"\*\*\* START OF THE PROJECT GUTENBERG EBOOK[^*\n]* \*\*\*"
            if match := re.search(header_end_pattern, header):
                header_end = match.end()
                header = header[:header_end]
            else:
                header_end = signature.end()
            for field, pattern in header_patterns.items():
                if match := re.search(pattern, header):
                    meta[field] = match[1]
                    header_end = max(header_end, match.end())
            return meta, header_end
        return {}, 0
