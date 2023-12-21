from django.core.management.base import BaseCommand, CommandError
from lexiflux.ebook.book_plain_text import import_plain_text


class Command(BaseCommand):
    help = 'Imports a book from an plain text file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the plain text file to import')

    def handle(self, *args, **options):
        file_path = options['file_path']
        try:
            import_plain_text(file_path)
            self.stdout.write(self.style.SUCCESS(f'Successfully imported book from "{file_path}"'))
        except Exception as e:
            raise CommandError(f'Error importing book: {e}')
