"""Import ebook from HTML."""

from lexiflux.ebook.book_loader_plain_text import BookLoaderPlainText


class BookLoaderHtml(BookLoaderPlainText):
    """Import ebook from HTML."""

    escape_html = False
