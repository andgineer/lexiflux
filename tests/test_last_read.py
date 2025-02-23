import pytest
import allure
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from lexiflux.models import Book, Author, Language, ReadingLoc

User = get_user_model()


@allure.epic("Pages endpoints")
@allure.feature("Library")
@pytest.mark.django_db
class TestFormatLastRead:
    @pytest.fixture
    def setup_book(self, db_init):
        author = Author.objects.create(name="Test Author")
        language = Language.objects.get(name="English")
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass"
        )
        book = Book.objects.create(title="Test Book", author=author, language=language)
        return book, user

    @allure.story("Format last read timestamp")
    @allure.title("Book never read")
    def test_never_read(self, setup_book):
        book, user = setup_book
        assert book.format_last_read(user) == "Never"

    @allure.story("Format last read timestamp")
    @allure.title("Book read within the last minute")
    def test_read_last_minute(self, setup_book):
        book, user = setup_book
        ReadingLoc.objects.create(
            user=user, book=book, last_access=timezone.now(), page_number=1, word=0
        )
        assert book.format_last_read(user) == "last minute"

    @allure.story("Format last read timestamp")
    @allure.title("Book read minutes ago")
    def test_read_minutes_ago(self, setup_book):
        book, user = setup_book
        ReadingLoc.objects.create(
            user=user,
            book=book,
            last_access=timezone.now() - timedelta(minutes=30),
            page_number=1,
            word=0,
        )
        assert book.format_last_read(user) == "30 minutes ago"

    @allure.story("Format last read timestamp")
    @allure.title("Book read hours ago")
    def test_read_hours_ago(self, setup_book):
        book, user = setup_book
        ReadingLoc.objects.create(
            user=user,
            book=book,
            last_access=timezone.now() - timedelta(hours=3),
            page_number=1,
            word=0,
        )
        assert book.format_last_read(user) == "3 hours ago"

    @allure.story("Format last read timestamp")
    @allure.title("Book read days ago")
    def test_read_days_ago(self, setup_book):
        book, user = setup_book
        ReadingLoc.objects.create(
            user=user,
            book=book,
            last_access=timezone.now() - timedelta(days=2),
            page_number=1,
            word=0,
        )
        assert book.format_last_read(user) == "2 days ago"

    @allure.story("Format last read timestamp")
    @allure.title("Book read weeks ago")
    def test_read_weeks_ago(self, setup_book):
        book, user = setup_book
        ReadingLoc.objects.create(
            user=user,
            book=book,
            last_access=timezone.now() - timedelta(weeks=3),
            page_number=1,
            word=0,
        )
        assert book.format_last_read(user) == "3 weeks ago"

    @allure.story("Format last read timestamp")
    @allure.title("Book read months ago")
    def test_read_months_ago(self, setup_book):
        book, user = setup_book
        ReadingLoc.objects.create(
            user=user,
            book=book,
            last_access=timezone.now() - timedelta(days=100),
            page_number=1,
            word=0,
        )
        assert book.format_last_read(user) == "3 months ago"

    @allure.story("Format last read timestamp")
    @allure.title("Book read years ago")
    def test_read_years_ago(self, setup_book):
        book, user = setup_book
        ReadingLoc.objects.create(
            user=user,
            book=book,
            last_access=timezone.now() - timedelta(days=400),
            page_number=1,
            word=0,
        )
        assert book.format_last_read(user) == "1 years ago"
