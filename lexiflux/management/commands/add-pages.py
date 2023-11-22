from django.core.management.base import BaseCommand, CommandError
from faker import Faker
from lexiflux.models import BookPage
from django.db.models import Max

NUM_PAGES_TO_ADD = 100


class Command(BaseCommand):
    help = '''Add pages with random content to the book.
    
    Usage: python manage.py add_pages <number of pages to add>
    
    By default, 100 pages are added.'''

    def add_arguments(self, parser):
        parser.add_argument('pages', nargs='?', type=int, default=NUM_PAGES_TO_ADD)

    def handle(self, *args, **options):
        fake = Faker()

        # Get the highest existing page number or default to 0 if no pages exist
        highest_page_number = BookPage.objects.aggregate(max_page_number=Max('number'))['max_page_number'] or 0

        for i in range(NUM_PAGES_TO_ADD):
            sentences = " ".join(fake.sentences(25))  # pylint: disable=invalid-name
            BookPage.objects.create(number=highest_page_number + i + 1, content=sentences)  # pylint: disable=no-member

        self.stdout.write(f"Added {NUM_PAGES_TO_ADD} pages from {highest_page_number + 1} to {highest_page_number + NUM_PAGES_TO_ADD}")
