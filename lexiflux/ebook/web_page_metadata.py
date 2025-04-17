import json
from typing import Any, Optional, cast
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from lexiflux.ebook.book_loader_base import MetadataField


class MetadataExtractor:
    """A class to extract metadata from web pages using multiple methods."""

    def __init__(self, html_content: str, url: str):
        """
        Initialize the metadata extractor.

        Args:
            html_content: HTML content as string
            url: Original URL of the content
        """
        self.soup = BeautifulSoup(html_content, "html.parser")
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
        self._extract_keywords()
        self._extract_image()

        return self.metadata

    def _get_meta_content(
        self,
        name: Optional[str] = None,
        property: Optional[str] = None,
    ) -> Optional[str]:
        """Helper method to get content from meta tags."""
        selector: dict[str, Any] = {}
        if name:
            selector["name"] = name
        if property:
            selector["property"] = property

        meta_tag = self.soup.find("meta", attrs=selector)
        if meta_tag and isinstance(meta_tag, Tag):
            content = meta_tag.get("content")
            if content and isinstance(content, str):
                return content.strip()
        return None

    def _extract_title(self) -> None:
        """Extract title using multiple methods."""
        if self.metadata.get(MetadataField.TITLE):
            return
        title_sources = [
            lambda: self._get_meta_content(name="dc.title"),  # Dublin Core
            lambda: self._get_meta_content(property="og:title"),  # Open Graph
            lambda: self._get_meta_content(name="twitter:title"),  # Twitter Card
            lambda: self.soup.find("title").get_text().strip()  # type: ignore
            if self.soup.find("title") and isinstance(self.soup.find("title"), Tag)
            else None,  # HTML title
            lambda: self.soup.find("h1").get_text().strip()  # type: ignore
            if self.soup.find("h1") and isinstance(self.soup.find("h1"), Tag)
            else None,  # First H1
            lambda: self.url.rsplit("/", 1)[-1]
            .replace("-", " ")
            .replace("_", " ")
            .capitalize(),  # URL fallback
        ]

        for source in title_sources:
            try:
                if title := source():
                    self.metadata[MetadataField.TITLE] = title
                    break
            except (AttributeError, TypeError):
                continue

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

        for source in author_sources:
            try:
                if author := source():
                    self.metadata[MetadataField.AUTHOR] = author
                    break
            except (AttributeError, TypeError):
                continue

    def _extract_language(self) -> None:
        """Extract language using multiple methods."""
        # Try different sources in order of preference
        language_sources = [
            lambda: self._get_meta_content(name="dc.language"),  # Dublin Core
            lambda: cast(Tag, self.soup.find("html")).get("lang", "").strip().split("-")[0]  # type: ignore
            if self.soup.find("html")
            and isinstance(self.soup.find("html"), Tag)
            and cast(Tag, self.soup.find("html")).get("lang")
            else None,  # HTML lang
            lambda: self._get_meta_content(property="og:locale").split("_")[0]  # type: ignore
            if self._get_meta_content(property="og:locale")
            else None,  # Open Graph locale
            lambda: self._get_meta_content(name="content-language"),  # Content-language
        ]

        for source in language_sources:
            try:
                if language := source():
                    self.metadata[MetadataField.LANGUAGE] = language
                    return
            except (AttributeError, TypeError):
                continue
        self.metadata[MetadataField.LANGUAGE] = None  # Default to None if no language found

    def _extract_date(self) -> None:
        """Extract publication date using multiple methods."""
        # Try different sources in order of preference
        date_sources = [
            lambda: self._get_meta_content(name="dc.date"),  # Dublin Core
            lambda: self._get_meta_content(name="dcterms.created"),  # Dublin Core terms
            lambda: self._get_meta_content(name="article:published_time"),  # Open Graph
            lambda: self._get_meta_content(name="publication_date"),  # Generic
            lambda: self._get_meta_content(name="date"),  # Generic
        ]

        for source in date_sources:
            try:
                if date := source():
                    # Add date standardization here if needed
                    self.metadata[MetadataField.RELEASED] = date
                    break
            except (AttributeError, TypeError):
                continue

    def _extract_credits(self) -> None:
        """Extract credits using multiple methods."""
        if self.metadata.get(MetadataField.CREDITS):
            return
        credit_sources = [
            lambda: self._get_meta_content(name="dc.publisher"),  # Dublin Core
            lambda: self._get_meta_content(name="generator"),  # Generator
            lambda: self._get_meta_content(property="og:site_name"),  # Open Graph site name
        ]

        for source in credit_sources:
            try:
                if credit := source():
                    self.metadata[MetadataField.CREDITS] = credit
                    break
            except (AttributeError, TypeError):
                continue

    def _extract_description(self) -> None:
        """Extract description using multiple methods."""
        # Try different sources in order of preference
        description_sources = [
            lambda: self._get_meta_content(name="dc.description"),  # Dublin Core
            lambda: self._get_meta_content(property="og:description"),  # Open Graph
            lambda: self._get_meta_content(name="twitter:description"),  # Twitter Card
            lambda: self._get_meta_content(name="description"),  # HTML meta description
        ]

        for source in description_sources:
            try:
                if description := source():
                    self.metadata["description"] = description
                    break
            except (AttributeError, TypeError):
                continue

    def _extract_keywords(self) -> None:
        """Extract keywords using multiple methods."""
        # Try different sources in order of preference
        keywords_sources = [
            lambda: self._get_meta_content(name="keywords"),  # HTML meta keywords
            lambda: self._get_meta_content(name="news_keywords"),  # News keywords
            lambda: [
                tag.get_text()
                for tag in self.soup.find_all("a", attrs={"rel": "tag"})
                if isinstance(tag, Tag)
            ],  # Tag links
        ]

        for source in keywords_sources:
            try:
                if keywords := source():
                    if isinstance(keywords, str):
                        keywords = [k.strip() for k in keywords.split(",")]
                    self.metadata["keywords"] = keywords
                    break
            except (AttributeError, TypeError):
                continue

    def _extract_image(self) -> None:
        """Extract main image using multiple methods."""
        # Try different sources in order of preference
        image_sources = [
            lambda: self._get_meta_content(property="og:image"),  # Open Graph
            lambda: self._get_meta_content(name="twitter:image"),  # Twitter Card
            lambda: cast(Tag, self.soup.find("link", attrs={"rel": "image_src"})).get("href")
            if self.soup.find("link", attrs={"rel": "image_src"})
            and isinstance(self.soup.find("link", attrs={"rel": "image_src"}), Tag)
            else None,  # Link rel
            lambda: cast(
                Tag,
                self.soup.find("img", attrs={"class": ["featured", "main", "hero"]}),
            ).get("src")
            if self.soup.find("img", attrs={"class": ["featured", "main", "hero"]})
            and isinstance(
                self.soup.find("img", attrs={"class": ["featured", "main", "hero"]}),
                Tag,
            )
            else None,  # Common image classes
        ]

        for source in image_sources:
            try:
                if image := source():
                    self.metadata["image"] = image
                    break
            except (AttributeError, TypeError):
                continue

    def _extract_json_ld(self) -> None:
        """Extract and parse JSON-LD structured data."""
        json_ld_tags = self.soup.find_all("script", attrs={"type": "application/ld+json"})

        for tag in json_ld_tags:
            try:
                if isinstance(tag, Tag) and tag.string:
                    data = json.loads(tag.string)

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
                self.metadata[MetadataField.TITLE] = item["headline"]

            if not self.metadata.get(MetadataField.AUTHOR) and "author" in item:
                author = item["author"]
                if isinstance(author, dict) and "name" in author:
                    self.metadata[MetadataField.AUTHOR] = author["name"]
                elif isinstance(author, list) and author and "name" in author[0]:
                    self.metadata[MetadataField.AUTHOR] = author[0]["name"]

            if not self.metadata.get(MetadataField.RELEASED) and "datePublished" in item:
                self.metadata[MetadataField.RELEASED] = item["datePublished"]

            if not self.metadata.get("description") and "description" in item:
                self.metadata["description"] = item["description"]

            if not self.metadata.get("image") and "image" in item:
                if isinstance(item["image"], dict) and "url" in item["image"]:
                    self.metadata["image"] = item["image"]["url"]
                elif isinstance(item["image"], str):
                    self.metadata["image"] = item["image"]

        # Handle WebPage type
        elif schema_type == "WebPage":
            if not self.metadata.get(MetadataField.TITLE) and "name" in item:
                self.metadata[MetadataField.TITLE] = item["name"]

            if not self.metadata.get("description") and "description" in item:
                self.metadata["description"] = item["description"]

        # Handle Organization type (for publisher)
        elif schema_type == "Organization":
            if not self.metadata.get(MetadataField.CREDITS) and "name" in item:
                self.metadata[MetadataField.CREDITS] = item["name"]


def extract_web_page_metadata(html_content: str, url: str) -> dict[str, Any]:
    """
    Extract metadata from HTML content using multiple methods.

    Args:
        html_content: HTML content as string
        url: Original URL of the content

    Returns:
        Dictionary with metadata fields as keys
    """
    extractor = MetadataExtractor(html_content, url)
    return extractor.extract_all()
