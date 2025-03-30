"""Import ebook from web pages."""

import datetime
import enum
import logging
from typing import Any, Optional, Union
from urllib.parse import urlparse

import requests
import trafilatura
from bs4 import BeautifulSoup

from lexiflux.ebook.book_loader_base import MetadataField
from lexiflux.ebook.book_loader_epub import clear_html
from lexiflux.ebook.book_loader_html import BookLoaderHtml

log = logging.getLogger()


class CleaningLevel(str, enum.Enum):
    """Cleaning level for web page content."""

    AGGRESSIVE = "aggressive"
    MODERATE = "moderate"
    MINIMAL = "minimal"


class BookLoaderURL(BookLoaderHtml):
    """Import ebook from web pages."""

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
            if "." in last_part:
                return last_part
            # Otherwise combine domain and path
            return f"{parsed_url.netloc}_{last_part}"

        # If no path, use the domain
        return parsed_url.netloc

    def load_text(self) -> str:
        """Fetch content from URL and apply cleaning according to the cleaning level."""
        try:
            response = requests.get(self.url, headers=self.headers, timeout=30)
            response.raise_for_status()
            html_content = response.text

            extracted_content = None
            if self.cleaning_level in (CleaningLevel.AGGRESSIVE, CleaningLevel.MODERATE):
                aggressive = self.cleaning_level == CleaningLevel.AGGRESSIVE
                target_language = self.languages[0] if self.languages else None

                extracted_content = trafilatura.extract(
                    html_content,
                    output_format="html",
                    include_comments=not aggressive,
                    favor_precision=aggressive,
                    favor_recall=not aggressive,
                    deduplicate=aggressive,
                    include_links=True,
                    include_images=True,
                    target_language=target_language,
                )
                log.info("Extracted content with trafilatura")
            if extracted_content is None:
                log.info("Using original HTML")
                extracted_content = self._process_minimal_cleaning(html_content)

            return self._add_source_info(extracted_content)

        except Exception as e:
            log.error(f"Error fetching URL {self.url}: {e}")
            raise

    def _process_minimal_cleaning(self, html_content: str) -> str:
        """Apply minimal cleaning to the HTML content."""
        # Use BeautifulSoup to parse and clean the HTML
        soup = BeautifulSoup(html_content, "html.parser")

        # Add title if available
        title = soup.find("title")
        title_text = title.get_text() if title else urlparse(self.url).netloc

        # Clean the HTML using the method from book_loader_epub
        cleaned_html = clear_html(str(soup))

        # Add source info at the beginning
        return self._add_source_info(cleaned_html, title_text)

    def _add_source_info(self, html_content: str, title: Optional[str] = None) -> str:
        """Add source information at the beginning of the content."""
        soup = BeautifulSoup(html_content, "html.parser")

        source_attrs: dict[str, str] = {"class": "source-info"}
        source_div = soup.new_tag("div", attrs=source_attrs)

        # Add a heading
        heading = soup.new_tag("h1")
        heading.string = title or "Web Page Import"
        source_div.append(heading)

        # Add source URL info
        source_p = soup.new_tag("p")
        source_p.string = f"Source: {self.url}"
        source_div.append(source_p)

        date_p = soup.new_tag("p")
        date_p.string = f"Imported on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        source_div.append(date_p)

        # Add horizontal rule
        hr = soup.new_tag("hr")
        source_div.append(hr)

        # Insert at the beginning of the body or document
        if soup.body:
            soup.body.insert(0, source_div)
        else:
            soup.insert(0, source_div)

        return str(soup)

    def detect_meta(self) -> tuple[dict[str, Any], int, int]:
        """Try to detect book meta from the web page."""
        meta: dict[str, Any] = {}
        start, end = 0, len(self.text)

        # If a title wasn't found, try to extract it from the URL
        if meta.get(MetadataField.TITLE) == "Unknown Title":
            parsed_url = urlparse(self.url)
            domain = parsed_url.netloc
            path = parsed_url.path.strip("/")

            if path:
                # Use the last part of the path, replace dashes and underscores with spaces
                parts = path.split("/")
                title = parts[-1].replace("-", " ").replace("_", " ").capitalize()
                meta[MetadataField.TITLE] = title
            else:
                # Use the domain as title
                meta[MetadataField.TITLE] = domain

        # Set the URL as author if not found
        if meta.get(MetadataField.AUTHOR) == "Unknown Author":
            parsed_url = urlparse(self.url)
            meta[MetadataField.AUTHOR] = parsed_url.netloc

        return meta, start, end
