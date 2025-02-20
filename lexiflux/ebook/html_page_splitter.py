"""Split HTML content into pages of approximately equal length."""

import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Optional

from bs4 import BeautifulSoup, NavigableString, Tag


@dataclass
class SplitterContext:
    """Context for holding mutable state during HTML splitting."""

    size: int
    chunk: list[str]

    def clear_chunk(self) -> None:
        """Clear the current chunk and reset size."""
        self.chunk.clear()
        self.size = 0

    def append_content(self, content: str) -> None:
        """Append content and update size."""
        self.chunk.append(content)
        self.size += len(content)


class HtmlPageSplitter:
    """Split HTML content into pages of approximately equal length."""

    def __init__(self, target_page_size: int) -> None:
        self.target_page_size = target_page_size

    def split_content(self, soup: BeautifulSoup) -> Iterator[str]:
        """Split content into pages using recursive tag handling."""
        contents = soup.body.contents if soup.body else soup.contents
        yield from self.split_elements(contents)

    def _has_content(self, html: str) -> bool:
        """Check if HTML contains any text content or images."""
        soup = BeautifulSoup(html, "html.parser")
        return bool(soup.get_text(strip=True) or soup.find("img"))

    def _non_empty_chunk(self, current_chunk: list[str]) -> Optional[str]:
        """Return chunk content if non-empty, otherwise None."""
        if current_chunk:
            chunk = "".join(current_chunk)
            if self._has_content(chunk):
                return chunk
        return None

    def split_elements(
        self,
        elements: list[Any],
        context: Optional[SplitterContext] = None,
    ) -> Iterator[str]:
        """Recursively split elements into chunks of appropriate size."""
        if context is None:
            context = SplitterContext(size=0, chunk=[])
        if context.chunk is None:
            context.chunk = []

        for element in elements:
            if isinstance(element, NavigableString):
                if text := str(element).strip():
                    yield from self._split_text(context, text)

            elif isinstance(element, Tag):
                yield from self._split_tag(context, element)

        # Yield any remaining content
        if context.chunk:  # noqa: SIM102
            if chunk := self._non_empty_chunk(context.chunk):
                yield chunk

    def _split_tag(self, context: SplitterContext, element: Any) -> Iterator[str]:
        """Convert tag to string to get its complete HTML representation."""
        tag_html = str(element)
        tag_size = len(tag_html)
        # If the entire tag is small enough, keep it together
        if tag_size <= self.target_page_size * 1.5:  # Allow slightly larger for complete tags
            if context.size + tag_size > self.target_page_size and context.chunk:
                if chunk := self._non_empty_chunk(context.chunk):
                    yield chunk
                context.chunk.clear()
                context.size = 0
            context.chunk.append(tag_html)
            context.size += tag_size
        else:
            # split large tags while preserving tag structure
            attrs_str = " ".join(f'{k}="{v}"' for k, v in element.attrs.items())
            space = " " if element.attrs else ""
            opening_tag = f"<{element.name}{space}{attrs_str}>"
            closing_tag = f"</{element.name}>"

            # If current chunk exists and adding opening tag would exceed size, yield it
            if context.chunk and context.size + len(opening_tag) > self.target_page_size:
                if chunk := self._non_empty_chunk(context.chunk):
                    yield chunk
                context.chunk.clear()
                context.size = 0

            # Add opening tag to new chunk
            context.chunk.append(opening_tag)
            context.size += len(opening_tag)

            # Process contents
            if element.contents:
                for content in self.split_elements(element.contents):
                    if context.size + len(content) + len(closing_tag) <= self.target_page_size:
                        context.chunk.append(content)
                        context.size += len(content)
                    else:
                        # End current chunk with closing tag
                        context.chunk.append(closing_tag)
                        if chunk := self._non_empty_chunk(context.chunk):
                            yield chunk
                        # Start new chunk with opening tag
                        context.chunk = [opening_tag, content]
                        context.size = len(opening_tag) + len(content)

            # Add closing tag to last chunk
            context.chunk.append(closing_tag)
            context.size += len(closing_tag)

    def _split_text(self, context: SplitterContext, text: str) -> Iterator[str]:
        sentences = re.split(r"([.!?。？！]+\s*)", text)
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            punctuation = sentences[i + 1] if i + 1 < len(sentences) else ""

            complete_sentence = sentence + (punctuation or "")
            sentence_size = len(complete_sentence)

            if context.size + sentence_size <= self.target_page_size:
                context.chunk.append(complete_sentence)
                context.size += sentence_size
            else:
                if chunk := self._non_empty_chunk(context.chunk):
                    yield chunk
                context.chunk.clear()
                context.size = 0

                # Handle sentences larger than target size
                if sentence_size > self.target_page_size:
                    words = complete_sentence.split()
                    temp: list[str] = []
                    temp_size = 0

                    for word in words:
                        word_size = len(word) + 1  # +1 for space
                        if temp_size + word_size > self.target_page_size and temp:
                            yield " ".join(temp)
                            temp = []
                            temp_size = 0
                        temp.append(word)
                        temp_size += word_size

                    if temp:
                        context.chunk.append(" ".join(temp))
                        context.size = temp_size
                else:
                    context.chunk.append(complete_sentence)
                    context.size = sentence_size
