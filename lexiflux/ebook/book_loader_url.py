"""Import ebook from web pages."""

import datetime
import enum
import logging
from pprint import pformat
from typing import Any, Optional, Union
from urllib.parse import urlparse

import requests
import trafilatura
from lxml import etree

from lexiflux.ebook.book_loader_base import MetadataField
from lexiflux.ebook.book_loader_html import BookLoaderHtml
from lexiflux.ebook.clear_html import clear_html, parse_partial_html
from lexiflux.ebook.web_page_metadata import extract_web_page_metadata
from lexiflux.timing import timing

log = logging.getLogger()


class CleaningLevel(str, enum.Enum):
    """Cleaning level for web page content."""

    AGGRESSIVE = "aggressive"
    MODERATE = "moderate"
    MINIMAL = "minimal"


class BookLoaderURL(BookLoaderHtml):
    """Import ebook from web pages."""

    title: str
    html_content: str
    tree_root: etree.Element

    def __init__(
        self,
        url: str,
        cleaning_level: Union[CleaningLevel, str] = CleaningLevel.MODERATE,
        languages: Optional[list[str]] = None,
        original_filename: Optional[str] = None,
    ) -> None:
        """Initialize.

        url - a URL to a webpage to import.
        cleaning_level - controls how aggressively content is cleaned:
            "aggressive" - use trafilatura to extract only main content
            "moderate" - use trafilatura but preserve more content
            "minimal" - minimal cleaning, preserves most of the original content
        """
        self.url = url
        self.cleaning_level = CleaningLevel(cleaning_level)

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            ),
        }

        super().__init__(url, languages, original_filename or self._get_filename_from_url())

    def _get_filename_from_url(self) -> str:
        """Extract a filename from the URL."""
        parsed_url = urlparse(self.url)
        path = parsed_url.path.strip("/")

        if path:
            # Use the last part of the path
            parts = path.split("/")
            last_part = parts[-1]
            # If the last part has a file extension, use it
            return last_part if "." in last_part else f"{parsed_url.netloc}_{last_part}"
        # If no path, use the domain
        return parsed_url.netloc

    def load_text(self):
        """Fetch content from URL and apply cleaning according to the cleaning level.

        Put the resulting text into self.text.
        Cache lxml tree root in self.tree_root.
        """
        try:
            with timing(f"Loading from {self.url}"):
                response = requests.get(self.url, headers=self.headers, timeout=30)
                response.raise_for_status()
                self.html_content = response.text

            with timing("Extracting readable HTML"):
                extracted_content = self.extract_readable_html()

            with timing("Parsing HTML"):
                self.tree_root = parse_partial_html(extracted_content)

            with timing("Adding source info"):
                self._add_source_info(self.tree_root)

            with timing("Cleared HTML"):
                self.text = clear_html(
                    root=self.tree_root,
                )

        except Exception as e:
            log.error(f"Error fetching URL {self.url}: {e}")
            raise

    def extract_readable_html(self):
        """Extract readable HTML content from the webpage."""
        extracted_content = None
        if self.cleaning_level in (CleaningLevel.AGGRESSIVE, CleaningLevel.MODERATE):
            aggressive = self.cleaning_level == CleaningLevel.AGGRESSIVE

            extracted_content = trafilatura.extract(
                self.html_content,
                output_format="html",
                include_comments=not aggressive,
                favor_precision=aggressive,
                favor_recall=not aggressive,
                deduplicate=aggressive,
                include_links=True,
                include_images=True,
            )
        if extracted_content is None:
            metadata = trafilatura.core.extract_metadata(self.html_content)
            log.info("Metadata extraction result: %s", pformat(metadata.as_dict()))

            log.info("Using original HTML")
            extracted_content = self.html_content
        return extracted_content

    def _add_source_info(self, root) -> None:
        """Add source information at the beginning of the content.

        Modifies root.
        """

        self.detect_meta()

        # Create source info div
        source_div = etree.Element("div", attrib={"class": "source-info"})

        # Add a heading
        heading = etree.Element("h1")
        heading.text = self.meta[MetadataField.TITLE]
        source_div.append(heading)

        # Add source URL info
        source_p = etree.Element("p")
        source_p.text = f"Source: {self.url}"
        source_div.append(source_p)

        # Add date info
        date_p = etree.Element("p")
        date_p.text = f"Imported on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        source_div.append(date_p)

        # Add horizontal rule
        hr = etree.Element("hr")
        source_div.append(hr)

        # Insert at the beginning of the body or document
        body = root.find("body")
        if body is not None:
            # If there's a body tag, insert at the beginning of the body
            body.insert(0, source_div)
        else:
            # If there's no body tag, insert at the beginning of the root
            root.insert(0, source_div)

    def detect_meta(self) -> tuple[dict[str, Any], int, int]:
        """Try to detect book meta from the web page.

        Do not recalculate if self.meta is already set.
        """
        if not self.meta:
            self.meta = extract_web_page_metadata(root=self.tree_root, url=self.url)

        # repeat even if meta is already set
        text_length = len(self.text) if hasattr(self, "text") and self.text is not None else 0
        self.book_start, self.book_end = 0, text_length

        if self.meta.get(MetadataField.LANGUAGE) is None and hasattr(self, "text"):
            self.meta[MetadataField.LANGUAGE] = self.detect_language()

        return self.meta, self.book_start, self.book_end
