"""Import a plain text file into Lexiflux."""
import re
from typing import IO, Any, Dict, Iterator, List, Optional, Union


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
    CHAPTER_HEADER_DISTANCE = 300  # Minimum character distance between chapter headers
    GUTENBERG_ENDING_SIZE = 30 * 1024  # Maximum size of the Gutenberg licence text
    GUTENBERG_START_SIZE = 1024  # Minimum size of the Gutenberg preamble

    def __init__(
        self, file_path: Union[str, IO[str]], languages: Optional[List[str]] = None
    ) -> None:
        """Initialize."""
        self.meta: Dict[str, Any] = {}
        if languages is None:
            languages = ["en", "sr"]
        self.languages = languages
        if isinstance(file_path, str):
            with open(file_path, "r", encoding="utf8") as file:
                self.text = file.read()
        else:
            self.text = file_path.read()
        # self.headings = self.get_headings()
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
            page_start_index
            + int(self.PAGE_LENGTH_TARGET * (1 + self.PAGE_LENGTH_ERROR_TOLERANCE)),
            self.book_end,
        )
        start_pos = max(
            page_start_index
            + int(self.PAGE_LENGTH_TARGET * (1 - self.PAGE_LENGTH_ERROR_TOLERANCE)),
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
            re.compile(r"\r?\n(\s*\r?\n)+"),  # Paragraph end
            re.compile(r"[^\s.!?]*\w[^\s.!?]*[.!?]\s"),  # Sentence end
            re.compile(r"\w+\b"),  # Word end
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
        text = re.sub(r"\r?\n(\s*\r?\n)+", "\n\n", text)
        text = re.sub(r"\r", "", text)
        text = re.sub(r"[^\S\n\r]+", " ", text)
        return text

    def pages(self) -> Iterator[str]:
        """Split a text into pages of approximately equal length."""
        start = self.book_start
        while start < self.book_end:
            end = self.find_nearest_page_end(start)
            page = self.normalize(self.text[start:end])
            # find chapters in the page
            # correct end if last one is inside PAGE_LENGTH_ERROR_TOLERANCE
            yield page
            start = end

    def get_headings(self, text: str) -> Dict[str, str]:
        """Detect chapter headings in the text."""
        patterns = self.prepare_heading_patterns()
        headings = {}
        lines = re.split(r"\n|<br/>", text)
        for i, line in enumerate(lines):
            line = line.replace("\r", "")
            # if line.upper() == line
            for pattern in patterns:
                if match := pattern.match(line):
                    headings[line] = f"{i}:{match.start()}"
                    break
        return headings

    def prepare_heading_patterns(self) -> List[re.Pattern[str]]:  # pylint: disable=too-many-locals
        """Prepare regex patterns for detecting chapter headings."""
        # Form 1: Chapter I, Chapter 1, Chapter the First, CHAPTER 1
        # Ways of enumerating chapters, e.g.
        arabic_numerals = r"\d+"
        roman_numerals = "(?=[MDCLXVI])M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})"
        number_words_by_tens = [
            "twenty",
            "thirty",
            "forty",
            "fifty",
            "sixty",
            "seventy",
            "eighty",
            "ninety",
        ]
        number_words = [
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
        ] + number_words_by_tens
        number_words_pat = "(" + "|".join(number_words) + ")"
        ordinal_number_words_by_tens = [
            "twentieth",
            "thirtieth",
            "fortieth",
            "fiftieth",
            "sixtieth",
            "seventieth",
            "eightieth",
            "ninetieth",
        ] + number_words_by_tens
        ordinal_number_words = (
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
            + [numberWord + "th" for numberWord in number_words]
            + ordinal_number_words_by_tens
        )
        ordinals_pat = "(the )?(" + "|".join(ordinal_number_words) + ")"
        enumerators_list = [arabic_numerals, roman_numerals, number_words_pat, ordinals_pat]
        enumerators = "(" + "|".join(enumerators_list) + ")"
        form1 = "(chapter|GLAVA|глава) " + enumerators

        # Form 2: II. The Mail
        enumerators = roman_numerals
        separators = r"(\. | )"
        title_case = "[A-Z][a-z]"
        form2 = enumerators + separators + title_case

        # Form 3: II. THE OPEN ROAD
        enumerators = roman_numerals
        separators = r"(\. )"
        title_case = "[A-Z][A-Z]"
        form3 = enumerators + separators + title_case

        # Form 4: a number on its own, e.g. 8, VIII
        arabic_numerals = r"^\d+\.?$"
        roman_numerals = r"(?=[MDCLXVI])M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})\.?$"
        enumerators_list = [arabic_numerals, roman_numerals]
        enumerators = "(" + "|".join(enumerators_list) + ")"
        form4 = enumerators

        pat = re.compile(form1, re.IGNORECASE)
        # This one is case-sensitive.
        pat2 = re.compile(f"({form2}|{form3}|{form4})")
        return [pat, pat2]

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
    splitter = BookPlainText("tests/resources/alice_adventure_in_wonderland.txt")
    print(
        splitter.meta,
        splitter.text[splitter.book_start : 1024],
        splitter.text[splitter.book_end - 100 : splitter.book_end],
    )
    # for page_content in splitter.pages():
    #     print(page_content)
