"""Import a book from a URL into Lexiflux."""

import logging
import re
from collections.abc import Iterator
from html import escape
from typing import Any, Literal, Optional
from urllib.parse import urlparse

import markdownify
import requests
from bs4 import BeautifulSoup
from readability import Document

from lexiflux.ebook.book_loader_base import BookLoaderBase, MetadataField
from lexiflux.ebook.headings import HeadingDetector
from lexiflux.ebook.page_splitter import PageSplitter

log = logging.getLogger()

# Define cleaning levels
CleaningLevel = Literal["aggressive", "moderate", "minimal"]


class BookLoaderURL(BookLoaderBase):
    """Import ebook from a URL."""

    escape_html = True

    def __init__(
        self,
        url: str,
        cleaning_level: CleaningLevel = "moderate",
        languages: Optional[list[str]] = None,
        original_filename: Optional[str] = None,
    ) -> None:
        """Initialize.

        url - a URL to a webpage to import.
        cleaning_level - controls how aggressively content is cleaned:
            "aggressive" - use readability to extract only main content
            "moderate" - use readability but preserve more content
            "minimal" - minimal cleaning, preserves most of the original content
        """
        self.url = url
        self.cleaning_level = cleaning_level
        self.file_path = url  # To maintain compatibility with the base class
        self.original_filename = original_filename or self._get_filename_from_url(url)
        self.languages = ["en", "sr"] if languages is None else languages
        self.meta, self.book_start, self.book_end = self.detect_meta()
        self.meta[MetadataField.TITLE], self.meta[MetadataField.AUTHOR] = self.get_title_author()
        self.meta[MetadataField.LANGUAGE] = self.get_language()

    def _get_filename_from_url(self, url: str) -> str:
        """Extract a suitable filename from the URL."""
        parsed_url = urlparse(url)
        path = parsed_url.path.rstrip("/")
        if path:
            # Get the last part of the path as the filename
            filename = path.split("/")[-1]
            if filename:
                return filename
        # Fallback to domain name
        return parsed_url.netloc

    def detect_meta(self) -> tuple[dict[str, Any], int, int]:
        """Try to detect book meta and text.

        Fetch the content, extract meta if it is present.
        Return: meta, start, end
        """
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                ),
            }
            response = requests.get(self.url, headers=headers, timeout=30)
            response.raise_for_status()

            html_content = response.text

            # Extract title and metadata
            soup = BeautifulSoup(html_content, "html.parser")
            title = self._extract_title(soup)
            author = self._extract_author(soup)
            language = self.detect_language_from_html(html_content)

            # Process content based on cleaning level
            if self.cleaning_level == "aggressive":
                # Original aggressive cleaning using readability
                doc = Document(html_content)
                readable_article = doc.summary()
                markdown_content = markdownify.markdownify(readable_article, heading_style="ATX")

            elif self.cleaning_level == "moderate":
                # Moderate cleaning - use readability but with more lenient settings
                doc = Document(html_content, min_text_length=25, retry_length=200)
                readable_article = doc.summary()
                # Use more permissive markdownify settings
                markdown_content = markdownify.markdownify(
                    readable_article,
                    heading_style="ATX",
                    strip=["script", "style", "form", "iframe"],  # Only strip these elements
                )

            else:  # minimal
                # Minimal cleaning - keep most content
                # Remove only scripts, styles, and other non-content elements
                for tag in soup.find_all(["script", "style", "iframe", "form", "nav"]):
                    tag.decompose()

                # Get the body or main content
                body = soup.find("body") or soup

                # Convert to markdown with minimal cleaning
                markdown_content = markdownify.markdownify(
                    str(body),
                    heading_style="ATX",
                    strip=["script", "style"],  # Minimal stripping
                )

            meta = {
                MetadataField.TITLE: title,
                MetadataField.AUTHOR: author if author else "Unknown Author",
                MetadataField.LANGUAGE: language,
                "cleaning_level": self.cleaning_level,  # Store the cleaning level used
            }

            self.text = markdown_content
            return meta, 0, len(markdown_content)

        except requests.RequestException as e:
            log.error(f"Error fetching URL: {e}")
            raise ValueError(f"Could not fetch content from URL: {e}") from e

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract the most likely title from the page."""
        # Try multiple sources for the title
        # 1. og:title meta tag
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):  # type: ignore
            return og_title.get("content")  # type: ignore

        # 2. Twitter title
        twitter_title = soup.find("meta", attrs={"name": "twitter:title"})
        if twitter_title and twitter_title.get("content"):  # type: ignore
            return twitter_title.get("content")  # type: ignore

        # 3. Standard title tag
        title_tag = soup.find("title")
        if title_tag and title_tag.string:  # type: ignore
            # Often title includes site name, try to clean it
            title_text = title_tag.string.strip()  # type: ignore
            # Common separators in titles
            for separator in [" | ", " - ", " – ", " — ", " // ", " » ", " : "]:
                if separator in title_text:
                    parts = title_text.split(separator, 1)
                    # Usually the first part is the article title, but check length
                    max_title_length = 10
                    if len(parts[0]) > max_title_length:
                        return parts[0].strip()
            return title_text

        # 4. First h1
        h1 = soup.find("h1")
        if h1 and h1.get_text(strip=True):
            return h1.get_text(strip=True)

        # Fallback
        return "Untitled Web Page"

    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract author information from various metadata sources."""
        # Try multiple sources for author info
        # 1. Explicit author meta tags
        for meta_tag in soup.find_all("meta"):
            if meta_tag.get("name", "").lower() in ["author", "twitter:creator", "article:author"]:  # type: ignore
                author = meta_tag.get("content", "")  # type: ignore
                if author:
                    return author.strip()  # type: ignore

        # 2. Open Graph article:author
        og_author = soup.find("meta", property="article:author")
        if og_author and og_author.get("content"):  # type: ignore
            return og_author.get("content").strip()  # type: ignore

        # 3. Common author class names/IDs
        author_selectors = [
            ".author",
            ".byline",
            '[itemprop="author"]',
            ".post-author",
            ".entry-author",
            ".writer",
            '[rel="author"]',
            ".article-author",
        ]
        for selector in author_selectors:
            author_elem = soup.select_one(selector)
            if author_elem and author_elem.get_text(strip=True):
                return author_elem.get_text(strip=True)

        return None

    def detect_language_from_html(self, html_content: str) -> Optional[str]:
        """Try to detect language from HTML lang attribute."""
        soup = BeautifulSoup(html_content, "html.parser")
        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):  # type: ignore
            return html_tag.get("lang").split("-")[0]  # type: ignore
        return None

    def get_random_words(self, words_num: int = 15) -> str:
        """Get random words from the book."""
        import random

        words = self.text.split()
        if len(words) <= words_num:
            return " ".join(words)

        start_idx = random.randint(0, len(words) - words_num)
        return " ".join(words[start_idx : start_idx + words_num])

    def normalize(self, text: str) -> str:
        """Make later processing more simple."""
        if self.escape_html:
            text = escape(text)
        text = re.sub(r"(\r?\n|\u2028|\u2029)", " <br/> ", text)
        text = re.sub(r"\r", "", text)
        return re.sub(r"[ \t]+", " ", text)

    def pages(self) -> Iterator[str]:
        """Split text into pages of approximately equal length."""

        page_splitter = PageSplitter(self.text, self.book_start, self.book_end)
        heading_detector = HeadingDetector()

        start = self.book_start
        self.toc = []
        page_num = 0
        while start < self.book_end:
            page_num += 1
            end = page_splitter.find_nearest_page_end(start)

            # shift end if found heading near the end
            if (  # noqa: SIM102
                hasattr(page_splitter, "PAGE_MIN_LENGTH")
                and start + page_splitter.PAGE_MIN_LENGTH < end
            ):
                if headings := heading_detector.get_headings(
                    page_splitter.text[start + page_splitter.PAGE_MIN_LENGTH : end] + "\n\n",
                    page_num,
                ):
                    end = (
                        start + page_splitter.PAGE_MIN_LENGTH + headings[0][1] - 1
                    )  # pos from first heading

            page_text = self.normalize(page_splitter.text[start:end])
            if headings := heading_detector.get_headings(page_text, page_num):
                self.toc.extend(headings)

            yield page_text
            assert end > start
            start = end
