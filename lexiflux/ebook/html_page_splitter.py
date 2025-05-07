"""Split HTML content into pages of approximately equal length."""

from collections.abc import Iterator
from dataclasses import dataclass
from html import escape
from typing import Optional

from lxml import etree

from lexiflux.ebook.clear_html import etree_to_str, parse_partial_html

TARGET_PAGE_SIZE = 3000


@dataclass
class SplitterContext:
    """Context for holding mutable state during HTML splitting."""

    size: int
    chunks: list[str]

    def clear_chunk(self) -> None:
        """Clear the current chunks and reset size."""
        self.chunks.clear()
        self.size = 0

    def append_content(self, content: str) -> None:
        """Append content and update size."""
        self.chunks.append(content)
        self.size += len(content)

    def append_text(self, text: str) -> None:
        """Append text and update size."""
        self.append_content(escape(text))


class HtmlPageSplitter:
    """Split HTML content into pages of approximately equal length."""

    def __init__(
        self,
        content: str = "",
        target_page_size: int = TARGET_PAGE_SIZE,
        root: Optional[etree._Element] = None,
    ) -> None:
        """Initialize the HTML page splitter.

        Args:
            content: HTML content string to split (optional if root is provided)
            target_page_size: Target size for each page in characters
            root: Parsed lxml element tree root (optional if content is provided)
        """
        self.target_page_size = target_page_size

        if root is not None:
            self.root = root
        elif content is not None:
            self.root = parse_partial_html(content)
        else:
            raise ValueError("Either content or root must be provided")

        # Find the body element or use the root if no body
        if self.root is None:
            self.elements = []
        else:
            body = self.root.find(".//body")
            self.elements = list(body) if body is not None else list(self.root)

    def pages(self) -> Iterator[str]:
        """Split content into pages."""
        yield from self._split_elements(self.elements)

    def _has_content(self, html: str) -> bool:
        """Check if HTML contains any text content or images."""
        root = parse_partial_html(html)
        if root is None:
            return False
        # Get all text from the document and check if there's any content
        text_content = self._get_text_content(root).strip()
        has_image = root.find(".//img") is not None
        return bool(text_content or has_image)

    def _get_text_content(self, element: etree._Element) -> str:
        """Extract all text content from an element and its children."""
        result = element.text or ""
        for child in element:
            result += self._get_text_content(child)
            if child.tail:
                result += child.tail
        return result

    def _non_empty_chunk(self, current_chunk: list[str]) -> Optional[str]:
        """Return chunk content if non-empty, otherwise None."""
        if current_chunk:
            chunk = "".join(current_chunk)
            if self._has_content(chunk):
                return chunk
        return None

    def _split_elements(
        self,
        elements: list[etree._Element],
        context: Optional[SplitterContext] = None,
    ) -> Iterator[str]:
        """Recursively split elements into chunks of appropriate size."""
        if context is None:
            context = SplitterContext(size=0, chunks=[])

        for element in elements:
            # Handle the element itself
            yield from self._split_tag(context, element)

            # Handle tail text (text after the closing tag)
            if element.tail and element.tail.strip():
                yield from self._split_text(context, element.tail)

        # Yield any remaining content
        if context.chunks:  # noqa: SIM102
            if chunk := self._non_empty_chunk(context.chunks):
                yield chunk

    def _split_tag(self, context: SplitterContext, element: etree._Element) -> Iterator[str]:  # noqa: C901,PLR0912,PLR0915
        """Convert tag to string and process it based on size."""
        tag_html = etree_to_str(element)
        tag_size = len(tag_html)

        # If the entire tag is small enough, keep it together
        if tag_size <= self.target_page_size * 1.5:  # Allow slightly larger for complete tags
            if context.size + tag_size > self.target_page_size and context.chunks:
                if chunk := self._non_empty_chunk(context.chunks):
                    yield chunk
                context.clear_chunk()

            context.append_content(tag_html)
        else:
            # Split large tags while preserving tag structure
            # Create opening and closing tags
            opening_tag = self._create_opening_tag(element)
            closing_tag = f"</{element.tag}>"

            # If current chunk exists and adding opening tag would exceed size, yield it
            if context.chunks and context.size + len(opening_tag) > self.target_page_size:
                if chunk := self._non_empty_chunk(context.chunks):
                    yield chunk
                context.clear_chunk()

            # Add opening tag to new chunk
            context.append_content(opening_tag)

            # First handle element's direct text content if it exists
            if element.text and element.text.strip():
                text = element.text
                if context.size + len(text) + len(closing_tag) <= self.target_page_size:
                    context.append_text(text)
                else:
                    # Split the text if needed
                    sentences = self._split_into_sentences(text)
                    for sentence in sentences:
                        if context.size + len(sentence) + len(closing_tag) <= self.target_page_size:
                            context.append_content(sentence)
                        # If the sentence itself is too large, split by words
                        elif len(sentence) > self.target_page_size:
                            words = sentence.split()
                            current_text = ""
                            for word in words:
                                if (
                                    len(current_text) + len(word) + 1 + len(closing_tag)
                                    <= self.target_page_size
                                ):
                                    if current_text:
                                        current_text += " "
                                    current_text += word
                                else:
                                    # Add current text fragment and close the tag
                                    context.append_text(current_text)
                                    context.append_content(closing_tag)
                                    if chunk := self._non_empty_chunk(context.chunks):
                                        yield chunk

                                    # Start a new chunk with opening tag
                                    context.chunks = [opening_tag]
                                    context.size = len(opening_tag)
                                    current_text = word

                            if current_text:
                                context.append_text(current_text)
                        else:
                            # End current chunk with closing tag
                            context.append_content(closing_tag)
                            if chunk := self._non_empty_chunk(context.chunks):
                                yield chunk

                            # Start new chunk with opening tag and the sentence
                            context.chunks = [opening_tag, sentence]
                            context.size = len(opening_tag) + len(sentence)

            # Now process child elements
            for child in element:
                child_str = etree_to_str(child)
                child_size = len(child_str)

                if context.size + child_size + len(closing_tag) <= self.target_page_size:
                    context.append_content(child_str)
                else:
                    # End current chunk with closing tag
                    context.append_content(closing_tag)
                    if chunk := self._non_empty_chunk(context.chunks):
                        yield chunk

                    # Start new chunk with opening tag
                    context.chunks = [opening_tag]
                    context.size = len(opening_tag)

                    # Process this child element
                    if child_size > self.target_page_size:
                        # Process the child element recursively if it's too large
                        for child_content in self._split_elements([child]):
                            # If child_content is small enough, add it to the current chunk
                            if (
                                context.size + len(child_content) + len(closing_tag)
                                <= self.target_page_size
                            ):
                                context.append_content(child_content)
                            else:
                                # End current chunk with closing tag
                                context.append_content(closing_tag)
                                if chunk := self._non_empty_chunk(context.chunks):
                                    yield chunk

                                # Start new chunk with opening tag and the child content
                                context.chunks = [opening_tag, child_content]
                                context.size = len(opening_tag) + len(child_content)
                    else:
                        context.append_content(child_str)

                # Handle child's tail text if any
                if child.tail and child.tail.strip():
                    tail_text = child.tail
                    if context.size + len(tail_text) + len(closing_tag) <= self.target_page_size:
                        context.append_text(tail_text)
                    else:
                        yield from self._split_text(context, tail_text, closing_tag, opening_tag)

            # Add closing tag to last chunk
            context.append_content(closing_tag)

    def _create_opening_tag(self, element: etree._Element) -> str:
        """Create the opening tag with attributes."""
        attrs = []
        for key, value in element.attrib.items():
            attrs.append(f'{key}="{value}"')

        attrs_str = " ".join(attrs)
        if attrs_str:
            return f"<{element.tag} {attrs_str}>"
        return f"<{element.tag}>"

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences using punctuation as separators."""
        result = []
        current = ""

        for char in text:
            current += char
            if char in ".!?":
                result.append(current)
                current = ""

        if current:
            result.append(current)

        return result if result else [text]

    def _split_text(  # noqa: C901,PLR0912
        self,
        context: SplitterContext,
        text: str,
        closing_tag: str = "",
        opening_tag: str = "",
    ) -> Iterator[str]:
        """Handle text content and split if necessary."""
        # If text fits in current chunk, add it
        if context.size + len(text) + len(closing_tag) <= self.target_page_size:
            context.append_text(text)
            return

        # Process by sentences
        sentences = self._split_into_sentences(text)
        for sentence in sentences:
            if context.size + len(sentence) + len(closing_tag) <= self.target_page_size:
                context.append_content(sentence)
            # If sentence is too long, split by words
            elif len(sentence) > self.target_page_size:
                words = sentence.split()
                current_text = ""
                for word in words:
                    if (
                        len(current_text) + len(word) + 1 + len(closing_tag)
                        <= self.target_page_size
                    ):
                        if current_text:
                            current_text += " "
                        current_text += word
                    else:
                        # Finish current chunk
                        if current_text:
                            context.append_text(current_text)
                        if closing_tag:
                            context.append_content(closing_tag)
                        if chunk := self._non_empty_chunk(context.chunks):
                            yield chunk

                        # Start new chunk
                        context.clear_chunk()
                        if opening_tag:
                            context.append_content(opening_tag)
                        current_text = word

                if current_text:
                    context.append_text(current_text)
            else:
                # End current chunk
                if closing_tag:
                    context.append_content(closing_tag)
                if chunk := self._non_empty_chunk(context.chunks):
                    yield chunk

                # Start new chunk
                context.clear_chunk()
                if opening_tag:
                    context.append_content(opening_tag)
                context.append_content(sentence)
