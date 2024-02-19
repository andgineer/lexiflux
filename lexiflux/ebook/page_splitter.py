"""Split text into pages"""
import re
from typing import Optional


class PageSplitter:
    """Split text into pages"""

    PAGE_LENGTH_TARGET = 3000  # Target page length in characters
    PAGE_LENGTH_ERROR_TOLERANCE = 0.25  # Tolerance for page length error
    assert 0 < PAGE_LENGTH_ERROR_TOLERANCE < 1
    PAGE_MIN_LENGTH = int(PAGE_LENGTH_TARGET * (1 - PAGE_LENGTH_ERROR_TOLERANCE))
    PAGE_MAX_LENGTH = int(PAGE_LENGTH_TARGET * (1 + PAGE_LENGTH_ERROR_TOLERANCE))

    def __init__(self, text: str, start: int, end: int):
        self.text = text
        self.start = start
        self.end = end

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
            self.end,
        )
        start_pos = max(
            page_start_index + int(self.PAGE_MIN_LENGTH),
            self.start,
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
        return min(page_start_index + self.end, page_start_index + self.PAGE_LENGTH_TARGET)
