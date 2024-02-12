"""Import a plain text file into Lexiflux."""
import logging
import random
import re
from typing import IO, Any, Dict, Iterator, List, Optional, Tuple, Union

from chardet.universaldetector import UniversalDetector
from lexiflux.ebook.book_base import MetadataField, BookBase
from lexiflux.ebook.headings import HeadingDetector

log = logging.getLogger()


class BookPlainText(BookBase):  # pylint: disable=too-many-instance-attributes
    """Import ebook from plain text."""

    PAGE_LENGTH_TARGET = 3000  # Target page length in characters
    PAGE_LENGTH_ERROR_TOLERANCE = 0.25  # Tolerance for page length error
    assert 0 < PAGE_LENGTH_ERROR_TOLERANCE < 1
    PAGE_MIN_LENGTH = int(PAGE_LENGTH_TARGET * (1 - PAGE_LENGTH_ERROR_TOLERANCE))
    PAGE_MAX_LENGTH = int(PAGE_LENGTH_TARGET * (1 + PAGE_LENGTH_ERROR_TOLERANCE))
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

    def __init__(
        self, file_path: Union[str, IO[str]], languages: Optional[List[str]] = None
    ) -> None:
        """Initialize.

        If file_path is a string, it is treated as a path to a file and we try to detect encoding.
        If file_path is a file object, we assume it was opened with correct encoding.
        """
        self.languages = ["en", "sr"] if languages is None else languages
        if isinstance(file_path, str):
            self.text = self.read_file(file_path)
        else:
            self.text = file_path.read()

        self.meta, self.book_start, self.book_end = self.detect_meta()
        self.meta[MetadataField.LANGUAGE] = self.get_language()

    def detect_meta(self) -> Tuple[Dict[str, Any], int, int]:
        """Try to detect book meta and text.

        Extract meta if it is present.
        Trim meta text from the beginning and end of the book text.
        Return: meta, start, end
        """
        meta, start = self.parse_gutenberg_header()
        end = self.cut_gutenberg_ending()
        if start > end:
            start = 0
            end = len(self.text)
        return meta, start, end

    def set_page_target(self, target_length: int, error_tolerance: int) -> None:
        """Set book page target length and error tolerance."""
        assert 0 < error_tolerance < 1
        self.PAGE_LENGTH_TARGET = target_length  # pylint: disable=invalid-name
        self.PAGE_LENGTH_ERROR_TOLERANCE = error_tolerance  # pylint: disable=invalid-name
        self.PAGE_MIN_LENGTH = int(  # pylint: disable=invalid-name
            self.PAGE_LENGTH_TARGET * (1 - self.PAGE_LENGTH_ERROR_TOLERANCE)
        )
        self.PAGE_MAX_LENGTH = int(  # pylint: disable=invalid-name
            self.PAGE_LENGTH_TARGET * (1 + self.PAGE_LENGTH_ERROR_TOLERANCE)
        )

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

    def find_nearest_page_end_match(
        self, page_start_index: int, pattern: re.Pattern[str], return_start: bool = False
    ) -> Optional[int]:
        """Find the nearest regex match around expected end of page.

        In no such match in the vicinity, return None.
        Calculate the vicinity based on the expected PAGE_LENGTH_TARGET
        and PAGE_LENGTH_ERROR_TOLERANCE.
        """
        end_pos = min(
            page_start_index + int(self.PAGE_MAX_LENGTH),
            self.book_end,
        )
        start_pos = max(
            page_start_index + int(self.PAGE_MIN_LENGTH),
            self.book_start,
        )
        ends = [
            match.start() if return_start else match.end()
            for match in pattern.finditer(self.text, start_pos, end_pos)
        ]
        return (
            min(ends, key=lambda x: abs(x - page_start_index + self.PAGE_LENGTH_TARGET))
            if ends
            else None
        )

    def find_nearest_page_end(self, page_start_index: int) -> int:
        """Find the nearest page end."""
        patterns = [  # sorted by priority
            re.compile(r"(\r?\n|\u2028|\u2029)(\s*(\r?\n|\u2028|\u2029))+"),  # Paragraph end
            re.compile(r"(\r?\n|\u2028|\u2029)"),  # Line end
            re.compile(r"[^\s.!?]*\w[^\s.!?]*[.!?]\s"),  # Sentence end
            re.compile(r"\w+\b"),  # Word end
        ]

        for pattern_idx, pattern in enumerate(patterns):
            if nearest_page_end := self.find_nearest_page_end_match(
                page_start_index, pattern, return_start=pattern_idx < 2
            ):
                return nearest_page_end

        # If no suitable end found, return the maximum allowed length
        return min(page_start_index + self.book_end, page_start_index + self.PAGE_LENGTH_TARGET)

    @staticmethod
    def normalize(text: str) -> str:
        """Make later processing more simple."""
        text = re.sub(r"(\r?\n|\u2028|\u2029)", " <br/> ", text)
        text = re.sub(r"\r", "", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text

    def pages(self) -> Iterator[str]:
        """Split a text into pages of approximately equal length.

        Also clear headings and recollect them during pages generation.
        """
        heading_detector = HeadingDetector()

        start = self.book_start
        self.toc = []
        page_num = 0
        while start < self.book_end:
            page_num += 1
            end = self.find_nearest_page_end(start)

            # shift end if found heading near the end
            if headings := heading_detector.get_headings(
                self.text[start + self.PAGE_MIN_LENGTH : end] + "\n\n", page_num
            ):
                end = start + self.PAGE_MIN_LENGTH + headings[0][1] - 1  # pos from first heading

            page_text = self.normalize(self.text[start:end])
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
