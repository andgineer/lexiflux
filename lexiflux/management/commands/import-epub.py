from django.core.management.base import BaseCommand, CommandError
from lexiflux.ebook.book_epub import import_book_from_epub  # Adjust the import path as necessary


class Command(BaseCommand):
    help = 'Imports a book from an EPUB file'

    def add_arguments(self, parser):
        parser.add_argument('epub_file_path', type=str, help='Path to the EPUB file to import')

    def handle(self, *args, **options):
        epub_file_path = options['epub_file_path']
        try:
            import_book_from_epub(epub_file_path)
            self.stdout.write(self.style.SUCCESS(f'Successfully imported book from "{epub_file_path}"'))
        except Exception as e:
            raise CommandError(f'Error importing book: {e}')
