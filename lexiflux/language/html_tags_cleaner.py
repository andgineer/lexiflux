"""Clean HTML tags from a string of HTML content."""

from html.parser import HTMLParser
from html import unescape
from typing import List

VALID_TAGS = set(HTMLParser.CDATA_CONTENT_ELEMENTS) | {
    "html",
    "head",
    "body",
    "div",
    "p",
    "span",
    "a",
    "img",
    "br",
    "hr",
    "table",
    "tr",
    "td",
    "th",
    "ul",
    "ol",
    "li",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "strong",
    "em",
    "b",
    "i",
    "u",
    "pre",
    "code",
}


class HTMLCleaner(HTMLParser):
    """HTML parser to clean tags from HTML content."""

    def __init__(self) -> None:
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.output: List[str] = []
        self.in_script_or_style = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self.in_script_or_style = True
        elif tag not in VALID_TAGS:
            self.output.append(self.get_starttag_text())  # type: ignore

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self.in_script_or_style = False
        elif tag not in VALID_TAGS:
            self.output.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if not self.in_script_or_style:
            self.output.append(data)

    def get_cleaned_data(self) -> str:
        """Return the cleaned HTML content."""
        return "".join(self.output)


def clear_html_tags(html_content: str) -> str:
    """Remove HTML tags from a string of HTML content."""
    parser = HTMLCleaner()
    parser.feed(html_content)
    cleaned_data = parser.get_cleaned_data()
    return unescape(cleaned_data)
