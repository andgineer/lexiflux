"""Import ebook from web pages."""

import datetime
import enum
import logging
import os
from pprint import pformat
from typing import Any, Optional, Union
from urllib.parse import urljoin, urlparse

import requests
import trafilatura
from bs4 import BeautifulSoup, Tag
from lxml import etree
from pagesmith import parse_partial_html, refine_html

from lexiflux.ebook.book_loader_base import MetadataField
from lexiflux.ebook.book_loader_html import BookLoaderHtml
from lexiflux.ebook.web_page_metadata import extract_web_page_metadata
from lexiflux.models import BookImage
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

            with timing("Extract metadata"):
                # Before extracting readable to not lose any metadata
                self.tree_root = parse_partial_html(self.html_content)
                self.detect_meta()

            with timing("Extracting IDs with internal links"):
                self.keep_ids = self.extract_ids_from_internal_links(self.tree_root)

            with timing("Extracting readable HTML"):
                extracted_content = self.extract_readable_html()

            with timing("Parse extracted HTML"):
                self.tree_root = parse_partial_html(extracted_content)

            with timing("Adding source info"):
                self._add_source_info()

            with timing("Cleared HTML"):
                self.text = refine_html(
                    root=self.tree_root,
                    ids_to_keep=self.keep_ids,
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
        if extracted_content is None:
            log.info("Using original HTML")
            extracted_content = self.html_content
        return extracted_content

    def _add_source_info(self) -> None:
        """Add source information at the beginning of the self.tree_root."""

        # Create source info div
        source_div = etree.Element("div", attrib={"class": "source-info"})

        # Add a heading
        heading = etree.Element("h1")
        heading.text = self.meta[MetadataField.TITLE]
        source_div.append(heading)

        # Add source URL info
        source_p = etree.Element("p")
        source_p.text = "Source: "

        # Create clickable link element
        source_link = etree.Element("a", attrib={"href": self.url, "target": "_blank"})
        source_link.text = self.url
        source_p.append(source_link)
        source_div.append(source_p)

        # Add date info
        date_p = etree.Element("p")
        date_p.text = f"Imported on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        source_div.append(date_p)

        # Add horizontal rule
        hr = etree.Element("hr")
        source_div.append(hr)

        if body := self.tree_root.xpath(".//body"):
            body[0].insert(0, source_div)
        elif html := self.tree_root.xpath(".//html"):
            html[0].insert(0, source_div)
        else:
            self.tree_root.insert(0, source_div)

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

    def create(self, owner_email, forced_language=None):
        """Include anchor_map in the book object and download images."""
        # Download images before creating the book so they can be referenced in pages
        self._prepare_images_for_download()

        book = super().create(owner_email, forced_language)
        book.anchor_map = self.anchor_map

        # Download and save images after the book is created
        self._download_and_save_images(book)

        return book

    def _prepare_images_for_download(self):
        """Prepare image metadata for download without actually downloading yet."""
        if not hasattr(self, "text") or not self.text:
            log.warning("No text content available for image processing")
            return

        self.image_mapping = {}  # Maps original src to new filename
        soup = BeautifulSoup(self.text, "html.parser")
        images = soup.find_all("img")

        if not images:
            log.info("No images found in the content")
            return

        log.info(f"Found {len(images)} images to prepare for download")

        for img_idx, img in enumerate(images):
            if not isinstance(img, Tag):
                continue

            src = img.get("src")
            if not src:
                continue

            # Convert relative URLs to absolute URLs
            absolute_url = urljoin(self.url, src)

            # Generate filename for this image
            parsed_url = urlparse(absolute_url)
            original_filename = os.path.basename(parsed_url.path)

            if not original_filename or "." not in original_filename:
                original_filename = f"image_{img_idx}.jpg"

            filename = self._sanitize_filename(original_filename)

            # Store mapping for later use
            self.image_mapping[src] = {
                "absolute_url": absolute_url,
                "filename": filename,
            }

        # Update image URLs in the text to point to our serve view
        # We'll use placeholder URLs that will be updated once we have the book code
        for img in images:
            src = img.get("src")
            if src in self.image_mapping:
                # Use a placeholder that we'll replace later
                img["src"] = f"__BOOK_IMAGE__{self.image_mapping[src]['filename']}"

        self.text = str(soup)

    def _download_and_save_images(self, book):
        """Download images from the web page and save them to the database."""
        if not hasattr(self, "image_mapping") or not self.image_mapping:
            log.info("No images to download")
            return

        for original_src, image_info in self.image_mapping.items():
            try:
                image_data, content_type, filename = self._download_image(
                    image_info["absolute_url"],
                    image_info["filename"],
                )

                if image_data:
                    BookImage.objects.create(
                        book=book,
                        image_data=image_data,
                        content_type=content_type,
                        filename=filename,
                    )

                    log.info(f"Downloaded and saved image: {filename}")

            except Exception as e:  # noqa: BLE001
                log.warning(f"Failed to download image {original_src}: {e}")
                continue

        # Update all book pages to replace placeholder URLs with actual URLs
        self._update_page_image_urls(book)

    def _download_image(self, image_url, filename):
        """Download a single image and return its data, content type, and filename."""
        try:
            log.debug(f"Downloading image: {image_url}")

            response = requests.get(
                image_url,
                headers=self.headers,
                timeout=30,
                stream=True,
            )
            response.raise_for_status()

            content_type = response.headers.get("content-type", "image/jpeg")
            image_data = response.content

            min_image_size = 100
            if len(image_data) < min_image_size:  # Very small files are probably not real images
                log.warning(f"Image too small, skipping: {image_url}")
                return None, None, None

            return image_data, content_type, filename

        except Exception as e:  # noqa: BLE001
            log.warning(f"Error downloading image {image_url}: {e}")
            return None, None, None

    def _update_page_image_urls(self, book):
        """Update all book pages to replace placeholder image URLs with actual URLs."""
        from django.urls import reverse

        for page in book.pages.all():
            content = page.content

            for _, image_info in self.image_mapping.items():
                placeholder = f"__BOOK_IMAGE__{image_info['filename']}"
                if placeholder in content:
                    actual_url = reverse(
                        "serve_book_image",
                        kwargs={"book_code": book.code, "image_filename": image_info["filename"]},
                    )
                    content = content.replace(placeholder, actual_url)

            if content != page.content:
                page.content = content
                page.save(update_fields=["content"])

    def _sanitize_filename(self, filename):
        """Sanitize filename to be safe for database storage."""
        safe_chars = "-_.abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        sanitized = "".join(c if c in safe_chars else "_" for c in filename)

        max_name_length = 200
        if len(sanitized) > max_name_length:
            name, ext = os.path.splitext(sanitized)
            sanitized = name[:190] + ext

        return sanitized
