"""Extract words from HTML content."""

import re
from html.parser import HTMLParser
from typing import List, Tuple, Optional

EXCLUDED_TAGS = ["style", "script"]


class HTMLWordExtractor(HTMLParser):
    """Extract words from HTML content."""

    def __init__(self) -> None:
        super().__init__()
        self.words: List[Tuple[int, int]] = []
        self.current_pos: int = 0
        self.ignore_content: bool = False

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        self.current_pos += len(self.get_starttag_text())  # type: ignore
        if tag in EXCLUDED_TAGS:
            self.ignore_content = True

    def handle_endtag(self, tag: str) -> None:
        self.current_pos += len(f"</{tag}>")
        if tag in EXCLUDED_TAGS:
            self.ignore_content = False

    def handle_startendtag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        self.current_pos += len(self.get_starttag_text())  # type: ignore

    def handle_data(self, data: str) -> None:
        if not self.ignore_content:
            for match in re.finditer(r"\S+", data):
                word = match.group()
                start = self.current_pos + match.start()
                end = start + len(word)
                self.words.append((start, end))
        self.current_pos += len(data)


def parse_words(content: str) -> List[Tuple[int, int]]:
    """Extract words from HTML content."""
    parser = HTMLWordExtractor()
    parser.feed(content)
    return parser.words
