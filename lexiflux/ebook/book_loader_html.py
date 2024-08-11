"""Import ebook from HTML."""

from lexiflux.ebook.book_loader_plain_text import BookLoaderPlainText


class BookHtml(BookLoaderPlainText):
    """Import ebook from HTML."""

    escape_html = False
