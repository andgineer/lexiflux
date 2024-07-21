"""Import ebook from HTML."""

from lexiflux.ebook.book_plain_text import BookPlainText


class BookHtml(BookPlainText):
    """Import ebook from HTML."""

    escape_html = False
