"""Populate the database with sample data."""
from faker import Faker

from lexiflux.models import BookPage

fake = Faker()

for i in range(100):
    sentences = " ".join(fake.sentences(25))  # pylint: disable=invalid-name
    BookPage.objects.create(
        number=i + 1, photo_url=f"https://picsum.photos/seed/{i+1}/600"
    )  # pylint: disable=no-member
