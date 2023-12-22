import logging
from django.core.management.base import BaseCommand, CommandError
from lexiflux.ebook.book_plain_text import import_plain_text, BookPlainText, MetadataField


VALID_LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']


def validate_log_level(log_level):
    if log_level.upper() not in VALID_LOG_LEVELS:
        valid_levels_str = ', '.join(VALID_LOG_LEVELS)
        raise CommandError(f"Invalid log level '{log_level}'. Valid options are: {valid_levels_str}")
    return log_level.upper()


class Command(BaseCommand):
    help = 'Imports a book from an plain text file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the plain text file to import')
        parser.add_argument(
            '--loglevel', type=str, help=f'Logging level (options: {", ".join(VALID_LOG_LEVELS)})',
            default='INFO'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        log_level = options['loglevel'].upper()

        # Configure Django logging level
        logging.basicConfig(level=getattr(logging, log_level, None))
        logging.getLogger('django').setLevel(getattr(logging, log_level, None))

        try:
            # todo: use import_plain_text
            splitter = BookPlainText(file_path)
            print(
                splitter.meta,
                splitter.text[splitter.book_start: 1024],
                splitter.text[splitter.book_end - 100: splitter.book_end],
            )
            splitter.meta[MetadataField.LANGUAGE] = ""
            splitter.detect_meta()
            print(splitter.meta)
            for page in splitter.pages():
                pass
            print(splitter.headings)
            # for page_content in splitter.pages():
            #     print(page_content)
            self.stdout.write(self.style.SUCCESS(f'Successfully imported book from "{file_path}"'))
        except Exception as e:
            raise CommandError(f'Error importing book from {file_path}: {e}')
