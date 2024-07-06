"""Extract words and HTML tags from HTML content."""

import re
from html.parser import HTMLParser
from typing import List, Tuple, Optional

EXCLUDED_TAGS = ["style", "script"]


class HTMLWordExtractor(HTMLParser):
    """Extract words and HTML tags from HTML content."""

    def __init__(self) -> None:
        super().__init__()
        self.words: List[Tuple[int, int]] = []
        self.tags: List[Tuple[int, int]] = []
        self.current_pos: int = 0
        self.ignore_content: bool = False
        self.ignored_tag_start: Optional[int] = None

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        start_pos = self.current_pos
        self.current_pos += len(self.get_starttag_text())  # type: ignore
        if tag in EXCLUDED_TAGS:
            self.ignore_content = True
            self.ignored_tag_start = start_pos
        else:
            self.tags.append((start_pos, self.current_pos))

    def handle_endtag(self, tag: str) -> None:
        if tag in EXCLUDED_TAGS and self.ignored_tag_start is not None:
            self.current_pos += len(f"</{tag}>")
            self.tags.append((self.ignored_tag_start, self.current_pos))
            self.ignore_content = False
            self.ignored_tag_start = None
        else:
            start_pos = self.current_pos
            self.current_pos += len(f"</{tag}>")
            self.tags.append((start_pos, self.current_pos))

    def handle_startendtag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        start_pos = self.current_pos
        self.current_pos += len(self.get_starttag_text())  # type: ignore
        self.tags.append((start_pos, self.current_pos))

    def handle_data(self, data: str) -> None:
        if not self.ignore_content:
            for match in re.finditer(r"(?:[\w'-]+(?:-[\w'-]+)*|[<>])", data):
                word = match.group()
                start = self.current_pos + match.start()
                end = start + len(word)
                self.words.append((start, end))
        self.current_pos += len(data)

    @classmethod
    def remove_html(
        cls, html_content: str, word_ids: List[Tuple[int, int]], tags_ids: List[Tuple[int, int]]
    ) -> Tuple[str, List[Tuple[int, int]]]:
        """Remove HTML tags from content and adjust word indices."""
        tags_to_remove = sorted(tags_ids, key=lambda x: x[0])
        plain_text = ""
        adjusted_indices = []
        current_pos = 0
        last_end = 0
        tag_index = 0

        for word_start, word_end in word_ids:
            # Add any content between last position and current word start, excluding tags
            while last_end < word_start:
                if tag_index < len(tags_to_remove) and tags_to_remove[tag_index][0] <= last_end:
                    # Skip tag
                    last_end = tags_to_remove[tag_index][1]
                    tag_index += 1
                else:
                    # Add non-tag content
                    next_tag_start = (
                        tags_to_remove[tag_index][0]
                        if tag_index < len(tags_to_remove)
                        else word_start
                    )
                    end_pos = min(next_tag_start, word_start)
                    plain_text += html_content[last_end:end_pos]
                    current_pos += end_pos - last_end
                    last_end = end_pos

            # Add the word and its adjusted index
            word = html_content[word_start:word_end]
            plain_text += word
            adjusted_indices.append((current_pos, current_pos + len(word)))
            current_pos += len(word)
            last_end = word_end

        # Add any remaining content after the last word, excluding tags
        while last_end < len(html_content):
            if tag_index < len(tags_to_remove) and tags_to_remove[tag_index][0] <= last_end:
                # Skip tag
                last_end = tags_to_remove[tag_index][1]
                tag_index += 1
            else:
                # Add non-tag content
                next_tag_start = (
                    tags_to_remove[tag_index][0]
                    if tag_index < len(tags_to_remove)
                    else len(html_content)
                )
                plain_text += html_content[last_end:next_tag_start]
                last_end = next_tag_start

        return plain_text, adjusted_indices


def parse_words(content: str) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
    """Extract words and HTML tags from HTML content."""
    parser = HTMLWordExtractor()
    parser.feed(content)
    return parser.words, parser.tags
