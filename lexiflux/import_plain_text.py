"""Import a plain text file into Lexiflux."""
import re
from typing import IO, Iterator, List, Optional, Union


class PageSplitter:
    """Split a text into pages of approximately equal length."""

    PAGE_LENGTH_TARGET = 3000
    PAGE_LENGTH_ERROR_TOLERANCE = 0.25

    def __init__(self, file_path: Union[str, IO[str]]) -> None:
        """Initialize PageSplitter."""
        if isinstance(file_path, str):
            with open(file_path, "r", encoding="utf8") as file:
                self.text = file.read()
        else:
            self.text = file_path.read()

    @staticmethod
    def find_nearest(ends: List[int], target: int) -> Optional[int]:
        """Find the point closest to the target page size."""
        return min(ends, key=lambda x: abs(x - target)) if ends else None

    def find_nearest_end(
        self, text: str, start_index: int, pattern: re.Pattern[str]
    ) -> Optional[int]:
        """Find the nearest end point based on the given pattern."""
        max_chars = int(self.PAGE_LENGTH_TARGET * (1 + self.PAGE_LENGTH_ERROR_TOLERANCE))
        min_chars = int(self.PAGE_LENGTH_TARGET * (1 - self.PAGE_LENGTH_ERROR_TOLERANCE))
        ends = [
            match.end()
            for match in pattern.finditer(text, start_index + min_chars, start_index + max_chars)
        ]
        return self.find_nearest(ends, start_index + self.PAGE_LENGTH_TARGET)

    def find_nearest_page_end(self, text: str, start_index: int) -> int:
        """Find the nearest page end."""
        patterns = [
            re.compile(r"(\r\n|\n\n)"),  # Paragraph end
            re.compile(r"[^\s.!?]*\w[^\s.!?]*[.!?]\s"),  # Sentence end
            re.compile(r"\w+\b"),  # Word end
        ]

        for pattern in patterns:
            if nearest_end := self.find_nearest_end(text, start_index, pattern):
                print(nearest_end, pattern)
                return nearest_end

        # If no suitable end found, return the maximum allowed length
        return min(len(text), start_index + self.PAGE_LENGTH_TARGET)

    def pages(self) -> Iterator[str]:
        """Split the text into pages."""
        start = 0
        while start < len(self.text):
            end = self.find_nearest_page_end(self.text, start)
            yield self.text[start:end]
            start = end


if __name__ == "__main__":
    splitter = PageSplitter("path_to_your_book.txt")
    for page_content in splitter.pages():
        print(page_content)
