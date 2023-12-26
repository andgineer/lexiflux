import logging
from django.core.management.base import BaseCommand, CommandError
from lexiflux.ebook.book_plain_text import BookPlainText, MetadataField
from lexiflux.models import Book, BookPage, Author, Language


def validate_log_level(level_name):
    level = logging.getLevelName(level_name.upper())
    if not isinstance(level, int):
        valid_levels = [name for name, value in logging._levelToName.items() if isinstance(value, str)]
        raise CommandError(f"Invalid log level '{level_name}'. Valid options are: {', '.join(valid_levels)}")
    return level


class Command(BaseCommand):
    help = 'Imports a book from an plain text file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the plain text file to import')
        parser.add_argument('--loglevel', type=str, help='Logging level for the command', default='INFO')
        parser.add_argument('--db-loglevel', type=str, help='Logging level for Django ORM', default='INFO')


    def handle(self, *args, **options):
        file_path = options['file_path']
        log_level = validate_log_level(options['loglevel'])
        db_log_level = validate_log_level(options['db_loglevel'])

        # Configure Django logging level
        logging.basicConfig(level=log_level)
        logging.getLogger('django').setLevel(log_level)
        logging.getLogger("django.db.backends").setLevel(db_log_level)

        try:
            # Process the book using BookPlainText
            book_processor = BookPlainText(file_path)

            # Create or get the author object
            author_name = book_processor.meta.get(MetadataField.AUTHOR, "Unknown Author")
            author, _ = Author.objects.get_or_create(name=author_name)

            # Create or get the language object
            language_code = book_processor.meta.get(MetadataField.LANGUAGE, "Unknown Language")
            language, _ = Language.objects.get_or_create(name=language_code)

            # Create the book object
            book_title = book_processor.meta.get(MetadataField.TITLE, "Unknown Title")
            book_instance = Book.objects.create(
                title=book_title,
                author=author,
                language=language
            )

            # Iterate over pages and save them
            for i, page_content in enumerate(book_processor.pages(), start=1):
                BookPage.objects.create(
                    book=book_instance,
                    number=i,
                    content=page_content
                )

            self.stdout.write(self.style.SUCCESS(f'Successfully imported book "{book_title}" ({author_name}, {language}) from "{file_path}"'))
        except Exception as e:
            raise CommandError(f'Error importing book from {file_path}: {e}')

