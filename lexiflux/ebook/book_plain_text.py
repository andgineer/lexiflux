"""Import a plain text file into Lexiflux."""
import re
from typing import IO, Any, Dict, Iterator, List, Optional, Tuple, Union


class MetadataField:  # pylint: disable=too-few-public-methods
    """Book metadata fields."""

    TITLE = "title"
    AUTHOR = "author"
    RELEASED = "released"
    LANGUAGE = "language"
    CREDITS = "credits"


class BookPlainText:
    """Import ebook from plain text."""

    PAGE_LENGTH_TARGET = 3000  # Target page length in characters
    PAGE_LENGTH_ERROR_TOLERANCE = 0.25  # Tolerance for page length error
    assert 0 < PAGE_LENGTH_ERROR_TOLERANCE < 1
    PAGE_MIN_LENGTH = int(PAGE_LENGTH_TARGET * (1 - PAGE_LENGTH_ERROR_TOLERANCE))
    PAGE_MAX_LENGTH = int(PAGE_LENGTH_TARGET * (1 + PAGE_LENGTH_ERROR_TOLERANCE))
    CHAPTER_HEADER_DISTANCE = 300  # Minimum character distance between chapter headers
    GUTENBERG_ENDING_SIZE = 30 * 1024  # Maximum size of the Gutenberg licence text
    GUTENBERG_START_SIZE = 1024  # Minimum size of the Gutenberg preamble

    def __init__(
        self, file_path: Union[str, IO[str]], languages: Optional[List[str]] = None
    ) -> None:
        """Initialize."""
        self.meta: Dict[str, Any] = {}
        self.headings: List[Tuple[str, str]] = []
        if languages is None:
            languages = ["en", "sr"]
        self.languages = languages
        if isinstance(file_path, str):
            with open(file_path, "r", encoding="utf8") as file:
                self.text = file.read()
        else:
            self.text = file_path.read()
        self.book_end = self.cut_gutenberg_ending()
        self.book_start = self.parse_gutenberg_header()

    def find_nearest_page_end_match(
        self, page_start_index: int, pattern: re.Pattern[str]
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
        ends = [match.end() for match in pattern.finditer(self.text, start_pos, end_pos)]
        return (
            min(ends, key=lambda x: abs(x - page_start_index + self.PAGE_LENGTH_TARGET))
            if ends
            else None
        )

    def find_nearest_page_end(self, page_start_index: int) -> int:
        """Find the nearest page end."""
        patterns = [  # sorted by priority
            re.compile(r"\r?\n(\s*\r?\n)+", re.UNICODE),  # Paragraph end
            re.compile(r"[^\s.!?]*\w[^\s.!?]*[.!?]\s", re.UNICODE),  # Sentence end
            re.compile(r"\w+\b", re.UNICODE),  # Word end
        ]

        for pattern in patterns:
            if nearest_page_end := self.find_nearest_page_end_match(page_start_index, pattern):
                # nearest_page_end = self.adjust_heading(page_start_index, nearest_page_end)
                return nearest_page_end

        # If no suitable end found, return the maximum allowed length
        return min(self.book_end, page_start_index + self.PAGE_LENGTH_TARGET)

    @staticmethod
    def normalize(text: str) -> str:
        """Make later processing more simple."""
        text = re.sub(r"\r?\n", "<br/>", text)
        text = re.sub(r"\r", "", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text

    def pages(self) -> Iterator[str]:
        """Split a text into pages of approximately equal length.

        Also clear headings and recollect them during pages generation.
        """
        start = self.book_start
        self.headings = []
        page_num = 0
        while start < self.book_end:
            page_num += 1
            end = self.find_nearest_page_end(start)

            # shift end if found heading near the end
            if headings := self.get_headings(
                self.text[start + self.PAGE_MIN_LENGTH : end], page_num
            ):
                end = self.PAGE_MIN_LENGTH + int(
                    headings[0][1].split(":")[1]
                )  # pos from first heading

            page_text = self.normalize(self.text[start:end])
            if headings := self.get_headings(page_text, page_num):
                self.headings.extend(headings)
            yield page_text
            assert end > start
            start = end

    def get_headings(self, page_text: str, page_num: int) -> List[Tuple[str, str]]:
        """Detect chapter headings in the text."""
        patterns = self.prepare_heading_patterns()
        headings: List[Tuple[str, str]] = []
        for pattern in patterns:
            if match := pattern.search(page_text):
                headings.append(
                    (match.group().replace("<br/>", " ").strip(), f"{page_num}:{match.start()}")
                )
                break
        return headings

    def prepare_heading_patterns(self) -> List[re.Pattern[str]]:  # pylint: disable=too-many-locals
        """Prepare regex patterns for detecting chapter headings."""
        # Form 1: Chapter I, Chapter 1, Chapter the First, CHAPTER 1
        # Ways of enumerating chapters, e.g.
        space = r"[ \t]"
        line_sep = rf"{space}*(\r?\n|<br\/>)"
        line_start = rf"{space}*(^|\r?\n|<br\/>)"
        arabic_numerals = r"\d+"
        roman_numerals = "(?=[MDCLXVI])M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})"
        number_words_by_tens_list = [
            "twenty",
            "thirty",
            "forty",
            "fifty",
            "sixty",
            "seventy",
            "eighty",
            "ninety",
        ]
        number_words_list = [
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
            "ten",
            "eleven",
            "twelve",
            "thirteen",
            "fourteen",
            "fifteen",
            "sixteen",
            "seventeen",
            "eighteen",
            "nineteen",
        ] + number_words_by_tens_list
        number_word = "(" + "|".join(number_words_list) + ")"
        ordinal_number_words_by_tens_list = [
            "twentieth",
            "thirtieth",
            "fortieth",
            "fiftieth",
            "sixtieth",
            "seventieth",
            "eightieth",
            "ninetieth",
        ] + number_words_by_tens_list
        ordinal_number_words_list = (
            [
                "first",
                "second",
                "third",
                "fourth",
                "fifth",
                "sixth",
                "seventh",
                "eighth",
                "ninth",
                "twelfth",
                "last",
            ]
            + [f"{numberWord}th" for numberWord in number_words_list]
        ) + ordinal_number_words_by_tens_list
        ordinal_word = "(the )?(" + "|".join(ordinal_number_words_list) + ")"
        enumerators = rf"({arabic_numerals}|{roman_numerals}|{number_word}|{ordinal_word})"
        delimiter = rf"(\.|{space}?){space}*"
        chapter_name = r"[\w \t '`\"’\?!:\/-]{1,120}"
        name_line = rf"{line_sep}{space}*{chapter_name}{space}*"

        templ_key_word = (
            rf"(chapter|glava|глава){space}+"
            rf"({enumerators}{delimiter})?({space}+{chapter_name}|{name_line})?"
        )
        templ_numbered = (
            rf"({arabic_numerals}|{roman_numerals}){delimiter}({chapter_name}|{name_line})?"
        )

        return [
            re.compile(
                f"{line_start}{templ_key_word}{line_sep}{line_sep}", re.IGNORECASE | re.UNICODE
            ),
            re.compile(
                f"{line_start}{templ_numbered}{line_sep}{line_sep}", re.IGNORECASE | re.UNICODE
            ),
        ]

    def ignore_close_headings(self, headings: List[int]) -> List[int]:
        """Ignore headings that are too close to each other, likely belonging to a TOC."""
        return [
            headings[i]
            for i in range(len(headings))
            if i == 0 or headings[i] - headings[i - 1] > self.CHAPTER_HEADER_DISTANCE
        ]

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

    def parse_gutenberg_header(self) -> int:
        """For books from Project Gutenberg cut off licence."""
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
            if match := re.search(header_end_pattern, header):
                header_end = match.end()
                header = header[:header_end]
            else:
                header_end = signature.end()
            for field, pattern in header_patterns.items():
                if match := re.search(pattern, header):
                    self.meta[field] = match[1]
                    header_end = max(header_end, match.end())
            return header_end
        return 0


if __name__ == "__main__":
    # splitter = BookPlainText("tests/resources/alice_adventure_in_wonderland.txt")
    splitter = BookPlainText("tests/resources/sherlock_holmes.txt")
    print(
        splitter.meta,
        splitter.text[splitter.book_start : 1024],
        splitter.text[splitter.book_end - 100 : splitter.book_end],
    )
    for page in splitter.pages():
        pass
    print(splitter.headings)
    # for page_content in splitter.pages():
    #     print(page_content)
