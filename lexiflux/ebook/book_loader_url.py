"""Import ebook from web pages."""

import datetime
import enum
import logging
import time
from pprint import pformat
from typing import Any, Optional, Union
from urllib.parse import urlparse

import requests
import trafilatura
from bs4 import BeautifulSoup

from lexiflux.ebook.book_loader_base import MetadataField
from lexiflux.ebook.book_loader_html import BookLoaderHtml
from lexiflux.ebook.clear_html import clear_html
from lexiflux.ebook.web_page_metadata import extract_web_page_metadata

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
        """Fetch content from URL and apply cleaning according to the cleaning level."""
        try:
            start_time = time.time()
            response = requests.get(self.url, headers=self.headers, timeout=30)
            response.raise_for_status()
            self.html_content = response.text
            elapsed_time = time.time() - start_time
            log.info(f"Loaded from {self.url} in {elapsed_time:.2f} seconds")

            extracted_content = None
            if self.cleaning_level in (CleaningLevel.AGGRESSIVE, CleaningLevel.MODERATE):
                aggressive = self.cleaning_level == CleaningLevel.AGGRESSIVE

                start_time = time.time()
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
                elapsed_time = time.time() - start_time
                log.info(f"Extracted content with trafilatura in {elapsed_time:.2f} seconds")
            if extracted_content is None:
                metadata = trafilatura.core.extract_metadata(self.html_content)
                log.info("Metadata extraction result: %s", pformat(metadata.as_dict()))

                log.info("Using original HTML")
                extracted_content = self.html_content

            start_time = time.time()
            self.text = clear_html(  # we need the self.text to calculate title in add_source_info
                extracted_content,
            )
            elapsed_time = time.time() - start_time
            log.info(f"Cleared HTML in {elapsed_time:.2f} seconds")

            start_time = time.time()
            self.text = self._add_source_info(self.text)
            elapsed_time = time.time() - start_time
            log.info(f"Added source info in {elapsed_time:.2f} seconds")
        except Exception as e:
            log.error(f"Error fetching URL {self.url}: {e}")
            raise

    def _add_source_info(self, html_content: str) -> str:
        """Add source information at the beginning of the content."""
        soup = BeautifulSoup(html_content, "html.parser")

        self.detect_meta()

        source_attrs: dict[str, str] = {"class": "source-info"}
        source_div = soup.new_tag("div", attrs=source_attrs)

        # Add a heading
        heading = soup.new_tag("h1")
        heading.string = self.meta[MetadataField.TITLE]
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
        """Try to detect book meta from the web page.

        Do not recalculate if self.meta is already set.
        """
        if not self.meta:
            self.book_start, self.book_end = 0, len(self.text)

            self.meta = extract_web_page_metadata(self.html_content, self.url)
            if self.meta[MetadataField.LANGUAGE] is None:
                self.meta[MetadataField.LANGUAGE] = self.detect_language()
        return self.meta, self.book_start, self.book_end
