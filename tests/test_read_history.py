import pytest
import allure
from django.utils import timezone
from datetime import timedelta
from lexiflux.models import ReadingLoc


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
class TestReadingLoc:
    @allure.story("Create Reading Location")
    def test_create_reading_loc(self, user, book):
        reading_loc = ReadingLoc.objects.create(user=user, book=book, page_number=1, word=1)
        assert reading_loc.user == user
        assert reading_loc.book == book
        assert reading_loc.page_number == 1
        assert reading_loc.word == 1
        assert reading_loc.jump_history == []
        assert reading_loc.current_jump == -1
        assert reading_loc.last_position_percent == 0.0

    @allure.story("Jump to New Location")
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
        assert reading_loc.last_position_percent == pytest.approx(
            50, 1
        )  # Assuming book has 5 pages

    @allure.story("Jump Back")
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
        assert reading_loc.last_position_percent == pytest.approx(
            25, 1
        )  # Assuming book has 5 pages

    @allure.story("Jump Forward")
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
        assert reading_loc.last_position_percent == pytest.approx(
            75, 1
        )  # Assuming book has 5 pages

    @allure.story("Update Reading Location")
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
        assert reading_loc.last_position_percent == pytest.approx(
            100, 1
        )  # Assuming book has 5 pages

    @allure.story("Last Access Time")
    def test_last_access_time(self, user, book):
        reading_loc = ReadingLoc.objects.create(user=user, book=book, page_number=1, word=1)
        assert reading_loc.last_access is None
        reading_loc.jump(2, 30)
        reading_loc.refresh_from_db()
        assert reading_loc.last_access is not None
        assert (timezone.now() - reading_loc.last_access) < timedelta(seconds=1)
