"""Import an EPUB file into the database."""
from typing import Any, Iterable, List

from ebooklib import ITEM_DOCUMENT, epub

from lexiflux.models import Author, Book, BookPage, Language


def extract_toc(toc: List[Any]) -> List[Any]:
    """Extract the table of contents from an EPUB.

    :param toc: A list representing the table of contents.
    :return: A list containing the structured table of contents.
    """
    print(f"Extracting TOC: {toc}")
    result: List[Any] = []

    if isinstance(toc, Iterable):
        for item_idx, item in enumerate(toc):
            if isinstance(item, tuple) and len(item) == 2:
                result.append({item[0].title: extract_toc(item[1])})
            elif isinstance(item, Iterable):
                result.append(extract_toc(list(item)))
            elif isinstance(item, epub.Link):
                result.append({item.title: item.href})
            elif isinstance(item, epub.Section):
                result.append({item.title: extract_toc(toc[item_idx + 1 :])})
                item_idx += 1

    return result


def import_book_from_epub(epub_file_path: str) -> None:
    """Import a book from an EPUB file."""
    book_epub = epub.read_epub(epub_file_path)

    # Extract title and author from the EPUB metadata
    title = (
        book_epub.get_metadata("DC", "title")[0][0]
        if book_epub.get_metadata("DC", "title")
        else "Unknown Title"
    )
    authors = book_epub.get_metadata("DC", "creator")
    author_name = authors[0][0] if authors else "Unknown Author"

    # Create or get the author object
    author, _ = Author.objects.get_or_create(name=author_name)

    # Extract language from the EPUB metadata
    language = book_epub.get_metadata("DC", "language")
    epub_language_code = language[0][0] if language else "en"  # Default to 'en' if not found

    book_instance = Book.objects.create(
        title=title,
        author=author,
        language=Language.objects.get_or_create(epub_code=epub_language_code)[0],
    )
    print(
        f"Created book: {book_instance.title}, {book_instance.author.name}, "
        f"{book_instance.language.name}"
    )

    book_toc = extract_toc(book_epub.toc)

    # Iterate through the spine items (usually chapters/pages)
    for index, spine_id in enumerate(book_epub.spine):
        item: epub.EpubItem = book_epub.get_item_with_id(spine_id[0])
        if item.get_type() == ITEM_DOCUMENT:
            print(
                f"Processing page: {spine_id[0]}",
                "name =",
                item.get_name(),
                "type =",
                item.get_type(),
                "id =",
                item.get_id(),
                "file_name =",
                item.file_name,
            )
            content = item.get_body_content().decode("utf-8")  # Decoding from bytes to string
            BookPage.objects.create(
                book=book_instance,
                number=index + 1,
                content=content,  # Page number
            )

    print(f"Book pages: {book_instance.pages.count()}")
    page = book_instance.pages.all()[15]
    print(f"Book pages: {page.content[:500]}")
    page = book_instance.pages.all()[16]
    print(f"Book pages: {page.content[:500]}")
    book_instance.content = book_toc
    book_instance.save()
    print(f"Book TOC: {book_toc}")


if __name__ == "__main__":
    import_book_from_epub(
        "/Users/ksfj595/shelf/books/Steven King/Ciklus Vukodlaka (323)/Ciklus Vukodlaka"
        " - Steven King.epub"
    )
