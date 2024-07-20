"""Clean HTML content and extract tag positions."""

import logging
from html.parser import HTMLParser
from html import unescape
from typing import List, Tuple

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
    "title",
}


logger = logging.getLogger(__name__)


class HTMLCleaner(HTMLParser):
    """Clean HTML content and extract tag positions."""

    def __init__(self) -> None:
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = False  # Changed to False to handle entities manually
        self.output: List[str] = []
        self.tag_positions: List[Tuple[int, int]] = []
        self.in_script_or_style = False
        self.current_position = 0
        self.is_self_closing = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_text = self.get_starttag_text()
        assert tag_text is not None
        start = self.current_position
        end = start + len(tag_text)
        if tag in ("script", "style"):
            self.in_script_or_style = True
        if tag in VALID_TAGS:
            self.tag_positions.append((start, end))
            self.is_self_closing = tag_text.endswith("/>")
            print(f"Tag: {tag}", self.tag_positions[-1])
        else:
            self.output.append(tag_text)
        self.current_position = end
        logger.debug(f"StartTag: {tag} current_position: {self.current_position}")

    def handle_endtag(self, tag: str) -> None:
        if self.is_self_closing:
            self.is_self_closing = False
            return
        start = self.current_position
        end = start + len(f"</{tag}>")
        if tag in ("script", "style"):
            self.in_script_or_style = False
        if tag in VALID_TAGS:
            self.tag_positions.append((start, end))
            logger.debug(f"End Tag: {tag} {self.tag_positions[-1]}")
        else:
            self.output.append(f"</{tag}>")
        self.current_position = end
        logger.debug(f"EndTag: {tag} current_position: {self.current_position}")

    def handle_data(self, data: str) -> None:
        if not self.in_script_or_style:
            self.output.append(data)
        else:
            self.tag_positions.append((self.current_position, self.current_position + len(data)))
            print(f"Hidden text: {data}", self.tag_positions[-1])
        self.current_position += len(data)
        logger.debug(f"Data: {data} current_position: {self.current_position}")

    def handle_entityref(self, name: str) -> None:
        entity = f"&{name};"
        unescaped = unescape(entity)
        self.output.append(unescaped)
        self.current_position += len(entity)
        logger.debug(
            f"EntityRef: {entity}, Unescaped: {unescaped} "
            f"current_position: {self.current_position}"
        )

    def handle_charref(self, name: str) -> None:
        char_ref = f"&#{name};"
        unescaped = unescape(char_ref)
        self.output.append(unescaped)
        self.current_position += len(char_ref)
        logger.debug(
            f"CharRef: {char_ref}, Unescaped: {unescaped} "
            f"current_position: {self.current_position}"
        )

    def handle_comment(self, data: str) -> None:
        start = self.current_position
        end = start + len(f"<!--{data}-->")
        self.tag_positions.append((start, end))
        self.current_position = end
        logger.debug(f"Comment: {data} current_position: {self.current_position}")

    def handle_decl(self, decl: str) -> None:
        start = self.current_position
        end = start + len(f"<!{decl}>")
        self.tag_positions.append((start, end))
        self.current_position = end
        logger.debug(f"Decl: {decl} current_position: {self.current_position}")

    def handle_pi(self, data: str) -> None:
        start = self.current_position
        end = start + len(f"<?{data}>")
        self.tag_positions.append((start, end))
        self.current_position = end
        logger.debug(f"PI: {data} current_position: {self.current_position}")

    def unknown_decl(self, data: str) -> None:
        start = self.current_position
        if data.startswith("CDATA["):
            # This is a CDATA section
            end = start + len(f"<![{data}]]>")
        else:
            # Other unknown declarations
            end = start + len(f"<!{data}>")
        self.tag_positions.append((start, end))
        self.current_position = end
        logger.debug(f"UnknownDecl: {data} current_position: {self.current_position}")

    def get_cleaned_data(self) -> Tuple[str, List[Tuple[int, int]]]:
        """Return cleaned data and tag positions."""
        return "".join(self.output), self.tag_positions


def parse_tags(html_content: str) -> Tuple[str, List[Tuple[int, int]]]:
    """Parse HTML content and return plain text and tag slices."""
    parser = HTMLCleaner()
    parser.feed(html_content)
    return parser.get_cleaned_data()


def clear_html_tags(html_content: str) -> str:
    """Remove HTML tags from content"""
    return parse_tags(html_content)[0]
