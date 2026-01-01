import json
import re
from collections.abc import Callable
from html import unescape
from typing import Any
from urllib.parse import urlparse

from lxml import etree
from pagesmith import parse_partial_html

from lexiflux.ebook.book_loader_base import MetadataField


class MetadataExtractor:
    """A class to extract metadata from web pages using multiple methods."""

    def __init__(
        self,
        html_content: str | None = None,
        *,
        url: str = "",
        tree: etree.Element | None = None,
    ) -> None:
        """
        Initialize the metadata extractor.

        Args:
            html_content: HTML content as string
            url: Original URL of the content
        """
        if tree is not None:
            parsed_tree = tree
        elif html_content:
            parsed_tree = parse_partial_html(html_content)
        else:
            parsed_tree = None
        self.tree: etree.Element = parsed_tree if parsed_tree is not None else etree.Element("html")
        # todo: add metadata from trafilature.extract_metadata()

        self.url = url
        self.metadata: dict[str, Any] = {}

    def extract_all(self) -> dict[str, Any]:
        """Extract all metadata from the page and return as a dictionary."""
        # Extract structured data
        self._extract_json_ld()

        # Extract standard metadata
        self._extract_title()
        self._extract_author()
        self._extract_language()
        self._extract_date()
        self._extract_credits()

        # Extract additional metadata
        self._extract_description()
        self._extract_image()

        return self.metadata

    def _get_meta_content(
        self,
        name: str | None = None,
        property: str | None = None,
    ) -> str | None:
        """Helper method to get content from meta tags."""
        xpath_query = "//meta"
        if name:
            xpath_query += f"[@name='{name}']"
        elif property:
            xpath_query += f"[@property='{property}']"

        if meta_tags := self.tree.xpath(xpath_query):
            content = meta_tags[0].get("content")
            if content and isinstance(content, str):
                return content.strip()
        return None

    def _get_first_match(self, sources: list[Callable]) -> Any | None:
        """Return the first non-None result."""
        for source in sources:
            try:
                if result := source():
                    return result
            except (AttributeError, TypeError, IndexError):
                continue

        return None

    def _extract_title(self) -> None:
        """Extract title using multiple methods."""
        if self.metadata.get(MetadataField.TITLE):
            return
        title_sources = [
            lambda: self._get_meta_content(name="dc.title"),  # Dublin Core
            lambda: self._get_meta_content(property="og:title"),  # Open Graph
            lambda: self._get_meta_content(name="twitter:title"),  # Twitter Card
            lambda: self._extract_title_from_tag(),  # HTML title
            lambda: self.tree.xpath("//h1/text()")[0].strip()
            if self.tree.xpath("//h1/text()")
            else None,  # First H1
            lambda: self.url.rsplit("/", 1)[-1]
            .replace("-", " ")
            .replace("_", " ")
            .capitalize(),  # URL fallback
        ]

        if title := self._get_first_match(title_sources):
            self.metadata[MetadataField.TITLE] = unescape(title)

    def _extract_title_from_tag(self) -> str | None:
        """Extract title from HTML title tag, handling broken HTML."""
        if text_nodes := self.tree.xpath("//title/text()"):
            title_text = text_nodes[0]
            # Handle broken HTML where title tag isn't closed:
            # Take only the first line to avoid including subsequent content
            first_line = title_text.split("\n", 1)[0]
            # Remove any HTML tags that might have been incorrectly included
            # as literal text due to unclosed title tag, while preserving actual text content
            # This regex removes HTML tags: <...> or </...>
            cleaned_text = re.sub(r"<[^>]+>", "", first_line)
            # If the cleaned text contains excessive whitespace (likely indicating
            # that subsequent content was incorrectly included), take only the first
            # meaningful chunk before the excessive whitespace
            # Look for patterns like "Title    More Text" where there are 3+ spaces
            if re.search(r"\s{3,}", cleaned_text):
                # Split on excessive whitespace and take the first part
                parts = re.split(r"\s{3,}", cleaned_text)
                cleaned_text = parts[0] if parts else cleaned_text
            return cleaned_text.strip() if cleaned_text.strip() else None
        return None

    def extract_part_title(self) -> str | None:
        """Extract title from part of a book."""
        title_sources = [
            lambda: self._get_meta_content(name="dc.title"),  # Dublin Core
            lambda: self._get_meta_content(property="og:title"),  # Open Graph
            lambda: self._get_meta_content(name="twitter:title"),  # Twitter Card
            lambda: self.tree.xpath("//title/text()")[0].strip()
            if self.tree.xpath("//title/text()")
            else None,
            # HTML title
            # Check all heading tags h1-h6 in a single lambda
            lambda: next(
                (
                    self.tree.xpath(f"//{h}/text()")[0].strip()
                    for h in ["h1", "h2", "h3", "h4", "h5", "h6"]
                    if self.tree.xpath(f"//{h}/text()")
                ),
                None,
            ),
            # title class elements - get all text nodes recursively
            lambda: " ".join(
                [
                    text.strip()
                    for text in self.tree.xpath("//*[contains(@class, 'title')]//text()")
                    if text.strip()
                ],
            )
            if self.tree.xpath("//*[contains(@class, 'title')]//text()")
            else None,
        ]

        return self._get_first_match(title_sources)

    def _extract_author(self) -> None:
        """Extract author using multiple methods."""
        if self.metadata.get(MetadataField.AUTHOR):
            return
        author_sources = [
            lambda: self._get_meta_content(name="dc.creator"),  # Dublin Core creator
            lambda: self._get_meta_content(name="dc.contributor"),  # Dublin Core contributor
            lambda: self._get_meta_content(name="author"),  # HTML meta author
            lambda: self._get_meta_content(property="article:author"),  # Open Graph article author
            lambda: self._get_meta_content(name="twitter:creator"),  # Twitter creator
            lambda: urlparse(self.url).netloc,  # Domain fallback
        ]

        if author := self._get_first_match(author_sources):
            self.metadata[MetadataField.AUTHOR] = unescape(author)

    def _extract_language(self) -> None:
        """Extract language using multiple methods."""
        # Try different sources in order of preference
        language_sources = [
            lambda: self._get_meta_content(name="dc.language"),  # Dublin Core
            lambda: self._extract_html_lang(),  # HTML lang extraction
            lambda: self._extract_og_locale(),  # Open Graph locale extraction
            lambda: self._get_meta_content(name="content-language"),  # Content-language
        ]

        self.metadata[MetadataField.LANGUAGE] = self._get_first_match(language_sources)

    def _extract_html_lang(self) -> str | None:
        """Extract language from HTML lang attribute."""
        lang_attrs = self.tree.xpath("//html/@lang")
        return lang_attrs[0].strip().split("-")[0] if lang_attrs else None

    def _extract_og_locale(self) -> str | None:
        """Extract language from Open Graph locale."""
        locale = self._get_meta_content(property="og:locale")
        return locale.split("_")[0] if locale else None

    def _extract_date(self) -> None:
        """Extract publication date using multiple methods."""
        # Try different sources in order of preference
        date_sources = [
            lambda: self._get_meta_content(name="dc.date"),  # Dublin Core
            lambda: self._get_meta_content(name="dcterms.created"),  # Dublin Core terms
            lambda: self._get_meta_content(name="article:published_time"),  # Open Graph
            lambda: self._get_meta_content(
                property="article:published_time",
            ),  # Open Graph (alternate)
            lambda: self._get_meta_content(name="publication_date"),  # Generic
            lambda: self._get_meta_content(name="date"),  # Generic
        ]

        if date := self._get_first_match(date_sources):
            self.metadata[MetadataField.RELEASED] = date

    def _extract_credits(self) -> None:
        """Extract credits using multiple methods."""
        if self.metadata.get(MetadataField.CREDITS):
            return
        credit_sources = [
            lambda: self._get_meta_content(name="dc.publisher"),  # Dublin Core
            lambda: self._get_meta_content(name="generator"),  # Generator
            lambda: self._get_meta_content(property="og:site_name"),  # Open Graph site name
        ]

        if credit := self._get_first_match(credit_sources):
            self.metadata[MetadataField.CREDITS] = unescape(credit)

    def _extract_description(self) -> None:
        """Extract description using multiple methods."""
        # Try different sources in order of preference
        description_sources = [
            lambda: self._get_meta_content(name="dc.description"),  # Dublin Core
            lambda: self._get_meta_content(property="og:description"),  # Open Graph
            lambda: self._get_meta_content(name="twitter:description"),  # Twitter Card
            lambda: self._get_meta_content(name="description"),  # HTML meta description
        ]

        if description := self._get_first_match(description_sources):
            self.metadata["description"] = unescape(description)

    def _extract_image(self) -> None:
        """Extract main image using multiple methods."""
        # Try different sources in order of preference
        image_sources = [
            lambda: self._get_meta_content(property="og:image"),  # Open Graph
            lambda: self._get_meta_content(name="twitter:image"),  # Twitter Card
            lambda: self.tree.xpath("//link[@rel='image_src']/@href")[0]
            if self.tree.xpath("//link[@rel='image_src']/@href")
            else None,  # Link rel
            lambda: self.tree.xpath(
                "//img[contains(@class, 'featured') or contains(@class, 'main') "
                "or contains(@class, 'hero')]/@src",
            )[0]
            if self.tree.xpath(
                "//img[contains(@class, 'featured') or contains(@class, 'main') "
                "or contains(@class, 'hero')]/@src",
            )
            else None,  # Common image classes
        ]

        if image := self._get_first_match(image_sources):
            self.metadata["image"] = image

    def _extract_json_ld(self) -> None:
        """Extract and parse JSON-LD structured data."""
        json_ld_tags = self.tree.xpath("//script[@type='application/ld+json']")

        for tag in json_ld_tags:
            try:
                if tag.text:
                    data = json.loads(tag.text)

                    # Handle single item
                    if isinstance(data, dict):
                        if "@graph" in data:
                            for item in data["@graph"]:
                                self._process_json_ld_item(item)
                        else:
                            self._process_json_ld_item(data)
                    # Handle array of items
                    elif isinstance(data, list):
                        for item in data:
                            self._process_json_ld_item(item)
            except (json.JSONDecodeError, AttributeError):
                continue

    def _process_json_ld_item(self, item: dict[str, Any]) -> None:  # noqa: C901,PLR0912
        """Process a single JSON-LD item."""
        # Extract data based on schema type
        schema_type = item.get("@type")

        if not schema_type:
            return

        # Handle Article type
        if schema_type in ["Article", "NewsArticle", "BlogPosting"]:
            if not self.metadata.get(MetadataField.TITLE) and "headline" in item:
                self.metadata[MetadataField.TITLE] = unescape(item["headline"])

            if not self.metadata.get(MetadataField.AUTHOR) and "author" in item:
                author = item["author"]
                if isinstance(author, dict) and "name" in author:
                    self.metadata[MetadataField.AUTHOR] = unescape(author["name"])
                elif isinstance(author, list) and author and "name" in author[0]:
                    self.metadata[MetadataField.AUTHOR] = unescape(author[0]["name"])

            if not self.metadata.get(MetadataField.RELEASED) and "datePublished" in item:
                self.metadata[MetadataField.RELEASED] = item["datePublished"]

            if not self.metadata.get("description") and "description" in item:
                self.metadata["description"] = unescape(item["description"])

            if not self.metadata.get("image") and "image" in item:
                if isinstance(item["image"], dict) and "url" in item["image"]:
                    self.metadata["image"] = item["image"]["url"]
                elif isinstance(item["image"], str):
                    self.metadata["image"] = item["image"]

        # Handle WebPage type
        elif schema_type == "WebPage":
            if not self.metadata.get(MetadataField.TITLE) and "name" in item:
                self.metadata[MetadataField.TITLE] = unescape(item["name"])

            if not self.metadata.get("description") and "description" in item:
                self.metadata["description"] = unescape(item["description"])

        # Handle Organization type (for publisher)
        elif schema_type == "Organization":
            if not self.metadata.get(MetadataField.CREDITS) and "name" in item:
                self.metadata[MetadataField.CREDITS] = unescape(item["name"])


def extract_web_page_metadata(
    html_content: str | None = None,
    *,
    url: str,
    root: etree.Element | None = None,
) -> dict[str, Any]:
    """
    Extract metadata from HTML content using multiple methods.

    Args:
        html_content: HTML content as string
        url: Original URL of the content

    Returns:
        Dictionary with metadata fields as keys
    """
    extractor = MetadataExtractor(html_content, url=url, tree=root)
    return extractor.extract_all()
