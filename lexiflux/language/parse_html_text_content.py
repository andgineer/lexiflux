"""Get text from HTML page and detect tag positions."""

import logging
from html import unescape
from html.parser import HTMLParser

TAGS_EXCLUDED_CONTENT = {"script", "style", "svg"}
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
    "sup",
}


logger = logging.getLogger(__name__)


class HTMLTextContentParser(HTMLParser):  # pylint: disable=too-many-instance-attributes
    """Get text content from HTML string and detect tag positions."""

    def __init__(self) -> None:
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = False  # Changed to False to handle entities manually
        self.output: list[str] = []
        self.tag_positions: list[tuple[int, int]] = []
        self.escaped_chars: list[tuple[int, int, str]] = []  # (start, end, unescaped)
        self.excluded_content = False
        self.current_position = 0
        self.is_self_closing = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:  # noqa: ARG002
        tag_text = self.get_starttag_text()
        assert tag_text is not None
        start = self.current_position
        end = start + len(tag_text)
        if tag in TAGS_EXCLUDED_CONTENT:
            self.excluded_content = True
        if tag in VALID_TAGS:
            self.tag_positions.append((start, end))
            self.is_self_closing = tag_text.endswith("/>")
            logger.debug(f"Tag: {tag} {self.tag_positions[-1]}")
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
            self.excluded_content = False
        if tag in VALID_TAGS:
            self.tag_positions.append((start, end))
            logger.debug(f"End Tag: {tag} {self.tag_positions[-1]}")
        else:
            self.output.append(f"</{tag}>")
        self.current_position = end
        logger.debug(f"EndTag: {tag} current_position: {self.current_position}")

    def handle_data(self, data: str) -> None:
        if not self.excluded_content:
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
        self.escaped_chars.append(
            (self.current_position, self.current_position + len(entity), unescaped),
        )
        self.current_position += len(entity)
        logger.debug(
            f"EntityRef: {entity}, Unescaped: {unescaped} "
            f"current_position: {self.current_position}",
        )

    def handle_charref(self, name: str) -> None:
        char_ref = f"&#{name};"
        unescaped = unescape(char_ref)
        self.output.append(unescaped)
        self.escaped_chars.append(
            (self.current_position, self.current_position + len(char_ref), unescaped),
        )
        self.current_position += len(char_ref)
        logger.debug(
            f"CharRef: {char_ref}, Unescaped: {unescaped} "
            f"current_position: {self.current_position}",
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

    def get_cleaned_data(self) -> tuple[str, list[tuple[int, int]], list[tuple[int, int, str]]]:
        """Return cleaned data, tag positions, and escaped character information."""
        return "".join(self.output), self.tag_positions, self.escaped_chars


def parse_html_content(
    html_content: str,
) -> tuple[str, list[tuple[int, int]], list[tuple[int, int, str]]]:
    """Parse HTML content and return plain text, tag slices, and escaped character information."""
    parser = HTMLTextContentParser()
    parser.feed(html_content)
    return parser.get_cleaned_data()


def extract_content_from_html(html_content: str) -> str:
    """Get just text content from HTML string."""
    return parse_html_content(html_content)[0]
