import pytest
import allure
from django.utils import timezone
from datetime import timedelta
from lexiflux.models import ReadingLoc, ReadingHistory


@allure.epic("Pages endpoints")
@allure.feature('Reader')
@pytest.mark.django_db
class TestReadingLoc:
    @allure.story('Create Reading Location')
    def test_create_reading_loc(self, user, book):
        reading_loc = ReadingLoc.objects.create(user=user, book=book, page_number=1, word=1)
        assert reading_loc.user == user
        assert reading_loc.book == book
        assert reading_loc.page_number == 1
        assert reading_loc.word == 1
        assert reading_loc.jump_history == []
        assert reading_loc.current_jump == -1

    @allure.story('Jump to New Location')
    def test_jump(self, user, book):
        reading_loc = ReadingLoc.objects.create(user=user, book=book, page_number=1, word=1)
        reading_loc.jump(3, 30)
        reading_loc.refresh_from_db()
        print(f"After jump: page_number={reading_loc.page_number}, word={reading_loc.word}")
        print(f"jump_history={reading_loc.jump_history}")
        print(f"current_jump={reading_loc.current_jump}")
        assert reading_loc.page_number == 3
        assert reading_loc.word == 30
        assert len(reading_loc.jump_history) == 1
        assert reading_loc.current_jump == 0
        assert reading_loc.jump_history[0] == {"page_number": 3, "word": 30}

    @allure.story('Jump Back')
    def test_jump_back(self, user, book):
        reading_loc = ReadingLoc.objects.create(user=user, book=book, page_number=1, word=1)
        reading_loc.jump(2, 30)
        reading_loc.jump(4, 50)
        page, word = reading_loc.jump_back()
        reading_loc.refresh_from_db()
        print(f"After jump_back: page_number={reading_loc.page_number}, word={reading_loc.word}")
        print(f"jump_history={reading_loc.jump_history}")
        print(f"current_jump={reading_loc.current_jump}")
        assert page == 2
        assert word == 30
        assert reading_loc.page_number == 2
        assert reading_loc.word == 30
        assert reading_loc.current_jump == 0
        assert len(reading_loc.jump_history) == 2
        assert reading_loc.jump_history[reading_loc.current_jump] == {"page_number": 2, "word": 30}

    @allure.story('Jump Forward')
    def test_jump_forward(self, user, book):
        reading_loc = ReadingLoc.objects.create(user=user, book=book, page_number=1, word=1)
        reading_loc.jump(2, 30)
        reading_loc.jump(4, 50)
        reading_loc.jump_back()
        page, word = reading_loc.jump_forward()
        reading_loc.refresh_from_db()
        print(f"After jump_forward: page_number={reading_loc.page_number}, word={reading_loc.word}")
        print(f"jump_history={reading_loc.jump_history}")
        print(f"current_jump={reading_loc.current_jump}")
        assert page == 4
        assert word == 50
        assert reading_loc.page_number == 4
        assert reading_loc.word == 50
        assert reading_loc.current_jump == 1
        assert len(reading_loc.jump_history) == 2
        assert reading_loc.jump_history[reading_loc.current_jump] == {"page_number": 4, "word": 50}

    @allure.story('Update Reading Location')
    def test_update_reading_location(self, user, book):
        reading_loc = ReadingLoc.objects.create(user=user, book=book, page_number=1, word=1)
        reading_loc.jump(2, 30)
        reading_loc.jump(4, 50)

        # Simulate scrolling to a new location
        ReadingLoc.update_reading_location(user, book.id, 5, 10)

        reading_loc.refresh_from_db()
        print(f"After update: page_number={reading_loc.page_number}, word={reading_loc.word}")
        print(f"jump_history={reading_loc.jump_history}")
        print(f"current_jump={reading_loc.current_jump}")

        assert reading_loc.page_number == 5
        assert reading_loc.word == 10
        assert reading_loc.current_jump == 1
        assert len(reading_loc.jump_history) == 2
        assert reading_loc.jump_history[reading_loc.current_jump] == {"page_number": 5, "word": 10}
        assert reading_loc.furthest_reading_page == 5
        assert reading_loc.furthest_reading_word == 10

    @allure.story('Update Reading History')
    def test_update_reading_history(self, user, book):
        reading_loc = ReadingLoc.objects.create(user=user, book=book, page_number=1, word=1)
        reading_loc.jump(3, 30)
        reading_loc.refresh_from_db()

        history = ReadingHistory.objects.get(user=user, book=book)

        total_pages = book.pages.count()
        expected_percent = (reading_loc.page_number - 1) / (total_pages - 1) if total_pages > 1 else 0.0

        print(f"Total pages: {total_pages}")
        print(f"Current page: {reading_loc.page_number}")
        print(f"Expected percent: {expected_percent}")
        print(f"Actual percent: {history.last_position_percent}")

        assert history.last_position_percent == pytest.approx(expected_percent, 0.01)
        assert (timezone.now() - history.last_opened) < timedelta(seconds=1)


@allure.epic("Pages endpoints")
@allure.feature('Reader')
@pytest.mark.django_db
class TestReadingHistory:
    @allure.story('Create Reading History')
    def test_create_reading_history(self, user, book):
        history = ReadingHistory.objects.create(user=user, book=book)
        assert history.user == user
        assert history.book == book
        assert history.last_position_percent == 0.0

    @allure.story('Update Reading History')
    def test_update_history(self, user, book):
        # Create initial reading location
        page_number = 3
        ReadingLoc.objects.create(user=user, book=book, page_number=page_number, word=1)

        # Update history
        ReadingHistory.update_history(user, book, page_number=page_number)

        history = ReadingHistory.objects.get(user=user, book=book)
        assert history.last_position_percent == 0.5  # 3 / 5, as the book has 5 pages
        assert (timezone.now() - history.last_opened) < timedelta(seconds=1)

    @allure.story('Unique Constraint')
    def test_unique_together_constraint(self, user, book):
        ReadingHistory.objects.create(user=user, book=book)
        with pytest.raises(Exception):  # This will raise an IntegrityError
            ReadingHistory.objects.create(user=user, book=book)