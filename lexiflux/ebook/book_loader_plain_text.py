"""Import a plain text file into Lexiflux."""

import logging
import random
import re
from typing import Any, Dict, Iterator, Tuple
from html import escape

from chardet.universaldetector import UniversalDetector
from lexiflux.ebook.book_loader_base import MetadataField, BookLoaderBase
from lexiflux.ebook.headings import HeadingDetector
from lexiflux.ebook.page_splitter import PageSplitter

log = logging.getLogger()


class BookLoaderPlainText(BookLoaderBase):  # pylint: disable=too-many-instance-attributes
    """Import ebook from plain text."""

    escape_html = True

    CHAPTER_HEADER_DISTANCE = 300  # Minimum character distance between chapter headers
    GUTENBERG_ENDING_SIZE = 30 * 1024  # Maximum size of the Gutenberg licence text
    GUTENBERG_START_SIZE = 1024  # Minimum size of the Gutenberg preamble
    JUNK_TEXT_BEGIN_PERCENT = 5
    JUNK_TEXT_END_PERCENT = 5
    assert JUNK_TEXT_END_PERCENT + JUNK_TEXT_BEGIN_PERCENT < 100
    WORD_ESTIMATED_LENGTH = 30
    MIN_RANDOM_WORDS = 3

    book_start: int
    book_end: int

    def detect_meta(self) -> Tuple[Dict[str, Any], int, int]:
        """Try to detect book meta and text.

        Extract meta if it is present.
        Trim meta text from the beginning and end of the book text.
        Return: meta, start, end
        """
        if isinstance(self.file_path, str):
            self.text = self.read_file(self.file_path)
        else:
            self.text = self.file_path.read()
        meta, start = self.parse_gutenberg_header()
        end = self.cut_gutenberg_ending()
        if start > end:
            start = 0
            end = len(self.text)
        return meta, start, end

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

        with open(file_path, "r", encoding=encoding) as f:
            return f.read()

    def get_random_words(self, words_num: int = 15) -> str:
        """Get random words from the book."""
        expected_words_length = self.WORD_ESTIMATED_LENGTH * words_num * 2
        start_index = int(len(self.text) * self.JUNK_TEXT_BEGIN_PERCENT / 100) + self.book_start
        end_index = (
            int(
                self.book_start
                + (self.book_end - self.book_start) * (100 - self.JUNK_TEXT_END_PERCENT) / 100
            )
            - expected_words_length
        )
        if end_index <= self.book_start:
            end_index = self.book_end

        start = random.randint(start_index, max(start_index, end_index))
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
        text = self.fix_coding(text)
        text = re.sub(r"(\r?\n|\u2028|\u2029)", " <br/> ", text)
        text = re.sub(r"\r", "", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text

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
        page_splitter = PageSplitter(self.text, self.book_start, self.book_end)
        heading_detector = HeadingDetector()

        start = self.book_start
        self.toc = []
        page_num = 0
        while start < self.book_end:
            page_num += 1
            end = page_splitter.find_nearest_page_end(start)

            # shift end if found heading near the end
            if headings := heading_detector.get_headings(
                page_splitter.text[start + page_splitter.PAGE_MIN_LENGTH : end] + "\n\n", page_num
            ):
                end = (
                    start + page_splitter.PAGE_MIN_LENGTH + headings[0][1] - 1
                )  # pos from first heading

            page_text = self.normalize(page_splitter.text[start:end])
            if headings := heading_detector.get_headings(page_text, page_num):
                self.toc.extend(headings)
            # todo: remove <br/> from the start of the page
            yield page_text
            assert end > start
            start = end

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

    def parse_gutenberg_header(self) -> Tuple[Dict[str, Any], int]:
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
        header_end_pattern = r"\*\*\* START OF THE PROJECT GUTENBERG EBOOK[^*\n]* \*\*\*"
        if signature := re.search(header_signature_pattern, header):
            meta = {}
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
