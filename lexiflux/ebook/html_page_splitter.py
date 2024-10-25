"""Split HTML content into pages of approximately equal length."""

from typing import Iterator, List, Any, Optional
import re
from bs4 import BeautifulSoup, Tag, NavigableString


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

    def split_elements(  # pylint: disable=too-many-branches,too-many-locals,too-many-statements
        self, elements: List[Any], current_size: int = 0, current_chunk: Optional[List[str]] = None
    ) -> Iterator[str]:
        """Recursively split elements into chunks of appropriate size.

        Args:
            elements: List of BeautifulSoup elements to process
            current_size: Running total of current chunk size
            current_chunk: Accumulated content for current page
        """
        if current_chunk is None:
            current_chunk = []

        for element in elements:  # pylint: disable=too-many-nested-blocks
            if isinstance(element, NavigableString):
                # Handle text content
                text = str(element).strip()
                if not text:
                    continue

                sentences = re.split(r"([.!?。？！]+\s*)", text)

                for i in range(0, len(sentences), 2):
                    sentence = sentences[i]
                    punctuation = sentences[i + 1] if i + 1 < len(sentences) else ""

                    complete_sentence = sentence + (punctuation or "")
                    sentence_size = len(complete_sentence)

                    if current_size + sentence_size <= self.target_page_size:
                        current_chunk.append(complete_sentence)
                        current_size += sentence_size
                    else:
                        chunk = "".join(current_chunk)
                        if self._has_content(chunk):
                            yield chunk
                        current_chunk.clear()
                        current_size = 0

                        # Handle sentences larger than target size
                        if sentence_size > self.target_page_size:
                            words = complete_sentence.split()
                            temp: List[str] = []
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
                                current_chunk.append(" ".join(temp))
                                current_size = temp_size
                        else:
                            current_chunk.append(complete_sentence)
                            current_size = sentence_size

            elif isinstance(element, Tag):
                # Convert tag to string to get its complete HTML representation
                tag_html = str(element)
                tag_size = len(tag_html)

                # If the entire tag is small enough, keep it together
                if (
                    tag_size <= self.target_page_size * 1.5
                ):  # Allow slightly larger for complete tags
                    if current_size + tag_size > self.target_page_size and current_chunk:
                        chunk = "".join(current_chunk)
                        if self._has_content(chunk):
                            yield chunk
                        current_chunk.clear()
                        current_size = 0
                    current_chunk.append(tag_html)
                    current_size += tag_size
                else:
                    # split large tags while preserving tag structure
                    attrs_str = " ".join(f'{k}="{v}"' for k, v in element.attrs.items())
                    space = " " if element.attrs else ""
                    opening_tag = f"<{element.name}{space}{attrs_str}>"
                    closing_tag = f"</{element.name}>"

                    # If current chunk exists and adding opening tag would exceed size, yield it
                    if current_chunk and current_size + len(opening_tag) > self.target_page_size:
                        chunk = "".join(current_chunk)
                        if self._has_content(chunk):
                            yield chunk
                        current_chunk.clear()
                        current_size = 0

                    # Add opening tag to new chunk
                    current_chunk.append(opening_tag)
                    current_size += len(opening_tag)

                    # Process contents
                    if element.contents:
                        for content in self.split_elements(element.contents):
                            if (
                                current_size + len(content) + len(closing_tag)
                                <= self.target_page_size
                            ):
                                current_chunk.append(content)
                                current_size += len(content)
                            else:
                                # End current chunk with closing tag
                                current_chunk.append(closing_tag)
                                chunk = "".join(current_chunk)
                                if self._has_content(chunk):
                                    yield chunk
                                # Start new chunk with opening tag
                                current_chunk = [opening_tag, content]
                                current_size = len(opening_tag) + len(content)

                    # Add closing tag to last chunk
                    current_chunk.append(closing_tag)
                    current_size += len(closing_tag)

        # Yield any remaining content
        if current_chunk:
            chunk = "".join(current_chunk)
            if self._has_content(chunk):
                yield chunk
