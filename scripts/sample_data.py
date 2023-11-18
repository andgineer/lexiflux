from lexiflux.models import BookPage
from faker import Faker
fake = Faker()

for i in range(100):
    sentences = ' '.join(fake.sentences(25))
    BookPage.objects.create(
        number=i + 1,
        photo_url=f"https://picsum.photos/seed/{i+1}/600"
    )
