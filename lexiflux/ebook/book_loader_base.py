"""Book base class for importing books from different formats."""

import logging
import os
from collections import Counter
from collections.abc import Iterator
from typing import IO, Any, cast
from urllib.parse import unquote

from django.core.management import CommandError
from lxml import etree
from pagesmith import parse_partial_html

from lexiflux.language.detect_language_fasttext import language_detector
from lexiflux.models import Author, Book, BookPage, CustomUser, Language, Toc, normalize_for_search
from lexiflux.timing import timing

log = logging.getLogger()


class MetadataField:  # pylint: disable=too-few-public-methods
    """Book metadata fields."""

    TITLE = "title"
    AUTHOR = "author"
    RELEASED = "released"
    LANGUAGE = "language"
    CREDITS = "credits"


class BookLoaderBase:
    """Base class for importing books from different formats."""

    toc: Toc = []
    meta: dict[str, Any]
    book_start: int
    book_end: int
    text: str

    html_content: str
    tree_root: etree.Element
    anchor_map: dict[str, dict[str, Any]]
    keep_ids: set[str]

    def __init__(
        self,
        file_path: str | IO[str],
        languages: list[str] | None = None,
        original_filename: str | None = None,
    ) -> None:
        """Initialize.

        file_path - a path to a file to import.
        """
        self.meta = {}
        self.anchor_map = {}
        self.keep_ids = set()
        self.file_path = file_path
        self.original_filename = original_filename
        self.languages = ["en", "sr"] if languages is None else languages
        self.load_text()
        self.meta, self.book_start, self.book_end = self.detect_meta()
        self.meta[MetadataField.TITLE], self.meta[MetadataField.AUTHOR] = self.get_title_author()
        self.meta[MetadataField.LANGUAGE] = self.get_language()

    def load_text(self) -> None:
        """Load the book text.

        Should put the text into self.text.
        """
        raise NotImplementedError()

    def detect_meta(self) -> tuple[dict[str, Any], int, int]:
        """Try to detect book meta and text.

        Read the book and extract meta if it is present.
        Trim meta text from the beginning and end of the book text.

        Should set self.meta, self.start, self.end
        And return them in result (mostly for tests compatibility)
        """
        raise NotImplementedError

    def create(self, owner_email: str | None, forced_language: str | None = None) -> Book:
        """Create the book instance."""
        title = self.meta[MetadataField.TITLE]
        author_name = self.meta[MetadataField.AUTHOR]
        author, _ = Author.objects.get_or_create(name=author_name)

        owner = None
        if owner_email:
            owner = CustomUser.objects.filter(email=owner_email).first()
            if not owner:
                # show users with email starting with partial --owner string
                users = CustomUser.objects.filter(email__istartswith=owner_email[:3])
                raise CommandError(
                    f'Error importing book: Cannot set owner "{owner_email}" - no such user'
                    + (f" (found: {', '.join(user.email for user in users)})" if users else ""),
                )

        language_name = forced_language or self.meta.get(MetadataField.LANGUAGE, "Unknown Language")
        language, _ = Language.objects.get_or_create(name=language_name)

        book_instance = Book.objects.create(title=title, author=author, language=language)
        if owner:
            book_instance.owner = owner
            book_instance.public = False
        else:
            book_instance.public = True

        self.toc = []
        self.anchor_map = {}
        with timing("Iterate over pages and save them"):
            if pages_to_add := [
                self.create_page(book_instance, i, page_content)
                for i, page_content in enumerate(self.pages(), start=1)
            ]:
                BookPage.objects.bulk_create(pages_to_add)

        # must be after page iteration and creation so the headings are collected
        book_instance.toc = self.toc
        book_instance.anchor_map = self.anchor_map
        log.debug("TOC: %s", book_instance.toc)

        return book_instance  # type: ignore

    def create_page(self, book_instance: Book, page_num: int, page_content: str) -> BookPage:
        """Create a book page instance.

        Can iteratively collect TOC.
        """
        return BookPage(
            book=book_instance,
            number=page_num,
            content=page_content,
            normalized_content=normalize_for_search(page_content),
        )

    @staticmethod
    def guess_title_author(filename: str) -> tuple[str, str]:
        """Guess the title and author from the filename."""
        if not filename:
            return "", ""
        # Remove the file extension
        name_without_extension = ".".join(filename.split(".")[:-1])

        if " - " not in name_without_extension:
            return name_without_extension.strip(), "Unknown Author"
        title, author = name_without_extension.split(" - ", 1)
        return title.strip(), author.strip()

    def get_title_author(self) -> tuple[str, str]:
        """Get title and author from meta or guess from filename."""
        title = self.meta.get(MetadataField.TITLE, "Unknown Title")
        author = self.meta.get(MetadataField.AUTHOR, "Unknown Author")

        if title == "Unknown Title" or author == "Unknown Author":
            filename = self.original_filename or (
                os.path.basename(
                    self.file_path
                    if isinstance(self.file_path, str)
                    else getattr(self.file_path, "name", ""),
                )
            )
            guessed_title, guessed_author = self.guess_title_author(filename)

            if title == "Unknown Title" and guessed_title:
                title = guessed_title

            if author == "Unknown Author" and guessed_author:
                author = guessed_author

        return title, author

    @staticmethod
    def get_language_group(lang: str) -> str:
        """Define language similarity groups."""
        lang_groups = {"group:bs-hr-sr": {"bs", "hr", "sr"}}
        return next(
            (group_name for group_name, group_langs in lang_groups.items() if lang in group_langs),
            lang,
        )

    def get_random_words(self, words_num: int = 15) -> str:
        """Get random words from the book."""
        raise NotImplementedError

    def pages(self) -> Iterator[str]:
        """Split a text into pages of approximately equal length.

        Also clear headings and recollect them during pages generation.
        Usually collect TOC but some loaders do that on iteratively in create_page().
        """
        raise NotImplementedError

    def detect_language(self) -> str | None:
        """Detect language of the book extracting random fragments of the `self.text`.

        Returns lang code.
        """
        languages = [language_detector().detect(self.get_random_words()) for _ in range(3)]

        # If no clear majority, try additional random fragments
        attempts = 0
        max_attempts = 10
        while attempts < max_attempts:
            lang_counter = Counter(map(self.get_language_group, languages))
            most_common_lang, most_common_count = lang_counter.most_common(1)[0]

            # Check if the most common language group count is more than the sum of other counts
            if most_common_count > sum(
                count for lang, count in lang_counter.items() if lang != most_common_lang
            ):
                break

            random_fragment = self.get_random_words()
            languages.append(language_detector().detect(random_fragment))
            attempts += 1

        # Count languages considering similarity groups
        lang_counter = Counter(map(self.get_language_group, languages))

        # Find the most common language group
        most_common_lang, _ = lang_counter.most_common(1)[0]

        # If the group consists of similar languages, find the most common individual language
        if most_common_lang.startswith("group:"):  # found lang group, should select just one lang
            result = Counter(
                [lang for lang in languages if self.get_language_group(lang) == most_common_lang],
            ).most_common(1)[0][0]
        else:
            result = most_common_lang

        if language_name := Language.find(name=result, google_code=result, epub_code=result):
            return language_name
        return None

    def get_language(self) -> str:
        """Get language from meta or detect from the book text."""
        if language_value := self.meta.get(MetadataField.LANGUAGE):  # noqa: SIM102
            if language_name := Language.find(
                name=language_value,
                google_code=language_value,
                epub_code=language_value,
            ):
                # Update the language to its name in case it was found by code
                log.debug("Language '%s' found in meta.", language_name)
                return language_name
        # Detect language if not found in meta
        language_name = self.detect_language()
        log.debug("Language '%s' detected.", language_name)
        return language_name  # type: ignore

    def _process_anchors(  # noqa: PLR0913
        self,
        page_num: int,
        content: str | None = None,
        html_tree: etree._Element | None = None,
        file_name: str = "",
        item_id: str | None = None,
        item_name: str | None = None,
    ):
        """Process anchors for a page.

        Store in self.anchor_map.
        """
        try:
            if content is not None:
                html_tree = parse_partial_html(content)
            elif html_tree is None:
                raise ValueError("content and html_tree is None")
            if html_tree is None:
                return
            for element in cast(etree.Element, html_tree.xpath("//*[@id]")):
                if anchor_id := element.get("id"):
                    link = f"{normalize_path(file_name)}#{anchor_id}"
                    if anchor_id not in self.keep_ids and element.tag != "a":
                        continue
                    current_item_id = item_id or anchor_id
                    element_text = element.text.strip() if element.text else ""
                    current_item_name = item_name or element_text[:100]

                    self.anchor_map[link] = {
                        "page": page_num,
                        "item_id": current_item_id,
                        "item_name": current_item_name,
                    }

            # Add an entry for the start of the document if it hasn't been added yet
            if file_name and file_name not in self.anchor_map:
                doc_item_id = item_id if item_id is not None else os.path.basename(file_name)
                doc_item_name = item_name if item_name is not None else os.path.basename(file_name)
                self.anchor_map[file_name] = {
                    "page": page_num,
                    "item_id": doc_item_id,
                    "item_name": doc_item_name,
                }

        except Exception:
            log.exception("Error processing anchors")

    @staticmethod
    def extract_ids_from_internal_links(root: etree.Element | None) -> set[str]:
        """Extract from self.tree_root IDs that have internal links to them.

        Extract both "#anchor" (as "anchor") and "filename#anchor" (as "anchor") formats
        as internal links, while ignoring external links like "http://..." or "https://...".
        """
        ids_to_keep: set[str] = set()
        if root is None:
            return ids_to_keep

        for link in root.xpath("//a[@href]"):
            href = link.get("href", "")
            if not href:
                continue

            if href.startswith(("http://", "https://", "ftp://", "mailto:")):
                continue

            element_id = href.split("#")[-1] if "#" in href else href
            if element_id:
                ids_to_keep.add(element_id)

        return ids_to_keep

    @staticmethod
    def find_anchor_word_position(page: BookPage, anchor_id: str) -> int:
        """Find word position for anchor ID in page content."""
        if not anchor_id:
            return 0

        # Search for id attribute in various formats
        search_patterns = [
            f'id="{anchor_id}"',
            f"id='{anchor_id}'",
            f"id={anchor_id}",  # unquoted (less common but possible)
        ]

        for pattern in search_patterns:
            anchor_pos = page.content.find(pattern)
            if anchor_pos != -1:
                return page.find_word_at_position(anchor_pos)

        log.warning(f"Anchor '{anchor_id}' not found in page {page.number} content")
        return 0


def normalize_path(path: str) -> str:
    """Normalize the image path by processing '.' / '..' and removing leading '/'."""
    path = unquote(path)
    components = path.split("/")
    normalized: list[str] = []
    for component in components:
        if component == "." or not component:
            continue
        if component == "..":
            if normalized:
                normalized.pop()
        else:
            normalized.append(component)
    return "/".join(normalized)
