from django.core.management.base import BaseCommand
from faker import Faker
from lexiflux.models import BookPage, Book, Author, Language
from django.db.models import Max

NUM_PAGES_TO_ADD = 100

class Command(BaseCommand):
    help = '''Add pages with random content to a book.

    Usage: python manage.py add_pages <number of pages to add>

    By default, 100 pages are added.'''

    def add_arguments(self, parser):
        parser.add_argument('pages', nargs='?', type=int, default=NUM_PAGES_TO_ADD)

    def handle(self, *args, **options):
        num_pages_to_add = options['pages']
        fake = Faker()

        # Ensure there is at least one author, language, and book
        author, _ = Author.objects.get_or_create(name=fake.name())
        language, _ = Language.objects.get_or_create(code='en', defaults={'name': 'English'})
        book, _ = Book.objects.get_or_create(title=fake.sentence(), defaults={'author': author, 'language': language})

        # Get the highest existing page number for the selected book or default to 0 if no pages exist
        highest_page_number = BookPage.objects.filter(book=book).aggregate(max_page_number=Max('number'))['max_page_number'] or 0

        for i in range(num_pages_to_add):
            sentences = " ".join(fake.sentences(25))
            BookPage.objects.create(book=book, number=highest_page_number + i + 1, content=sentences)

        self.stdout.write(f"Added {num_pages_to_add} pages from {highest_page_number + 1} to {highest_page_number + num_pages_to_add}")


