import pytest
import allure
from datetime import datetime, timedelta

import pytz
from django.utils import timezone
import os

from tests.page_models.words_export_page import WordsExportPage
from tests.conftest import USER_PASSWORD
from lexiflux.models import WordsExport


@allure.epic('End-to-end (selenium)')
@allure.feature('Words Export Page')
@allure.story('User without translation history')
@pytest.mark.docker
@pytest.mark.selenium
@pytest.mark.django_db
def test_words_export_page_no_history(browser, approved_user):
    browser.login(approved_user, USER_PASSWORD)
    page = WordsExportPage(browser)
    page.goto()

    with allure.step("Check error message for user without translation history"):
        error_message = page.get_error_message()
        assert "Your translation history is empty. Please translate some words before exporting." in error_message

    with allure.step("Verify form controls are hidden"):
        assert not page.is_form_controls_visible()
        assert not page.is_export_button_enabled()

@allure.epic('End-to-end (selenium)')
@allure.feature('Words Export Page')
@allure.story('User with translation history but no previous exports')
@pytest.mark.docker
@pytest.mark.selenium
@pytest.mark.django_db
def test_words_export_page_with_history_no_exports(browser, user_with_translations, language):
    browser.login(user_with_translations, USER_PASSWORD)
    page = WordsExportPage(browser)
    page.goto()

    with allure.step("Verify form is visible"):
        assert page.is_form_controls_visible()

    with allure.step("Check default values"):
        assert page.is_export_button_enabled()
        assert page.get_selected_language() == language.name
        assert page.get_selected_export_method() == 'ankiConnect'
        assert page.get_deck_name() == 'Lexiflux - English'

@allure.epic('End-to-end (selenium)')
@allure.feature('Words Export Page')
@allure.story('User with previous words exports')
@pytest.mark.docker
@pytest.mark.selenium
@pytest.mark.django_db
def test_words_export_page_with_previous_exports(browser, user_with_translations, language, translation_history):
    # Create a previous export with timezone-aware datetime
    last_export_time = timezone.now().replace(microsecond=0, second=0) - timedelta(days=1)
    deck_name = 'Previous Deck'
    export_format = 'ankiConnect'
    WordsExport.objects.create(
        user=user_with_translations,
        language=language,
        export_datetime=last_export_time,
        word_count=10,
        deck_name=deck_name,
        export_format=export_format
    )

    browser.login(user_with_translations, USER_PASSWORD)
    page = WordsExportPage(browser)
    page.goto()

    with allure.step("Verify form is pre-filled with last export data"):
        assert page.get_selected_language() == language.name

        # Get the datetime from the page
        page_datetime_str = page.get_min_datetime()

        # Parse the datetime string from the page
        page_datetime = datetime.strptime(page_datetime_str, '%Y-%m-%dT%H:%M')

        # Make page_datetime timezone-aware (assume UTC)
        page_datetime = pytz.utc.localize(page_datetime)

        # Convert both datetimes to UTC for comparison
        last_export_time_utc = last_export_time.astimezone(pytz.utc)
        page_datetime_utc = page_datetime.astimezone(pytz.utc)

        # Compare the datetimes, allowing for a small difference due to processing time
        assert page_datetime_utc == last_export_time_utc, \
            f"Expected datetime close to {last_export_time_utc}, but got {page_datetime_utc}"

        assert page.get_selected_export_method() == export_format
        assert page.get_deck_name() == deck_name

@allure.epic('End-to-end (selenium)')
@allure.feature('Words Export Page')
@allure.story('Export words as CSV file')
@pytest.mark.docker
@pytest.mark.selenium
@pytest.mark.django_db
def test_words_export_csv_file(browser, user_with_translations, language, translation_history):
    browser.login(user_with_translations, USER_PASSWORD)
    page = WordsExportPage(browser)
    page.goto()

    with allure.step("Select CSV file export method"):
        page.select_export_method('csvFile')

    with allure.step("Click export button"):
        page.click_export_button()

    if browser.browser_name != 'Edge':
        with allure.step("Wait for download to complete"):
            assert page.wait_for_download(), "CSV file was not downloaded"

        with allure.step("Verify CSV file download"):
            csv_file = page.get_latest_csv_file()
            assert csv_file is not None, "No CSV file was found in the downloads directory"
            assert os.path.getsize(csv_file) > 0, "Downloaded CSV file is empty"
    else:
        with allure.step("Verify CSV file download (simulated for Edge)"):
            csv_file = page.get_latest_csv_file()
            assert csv_file == "csv_file_simulated", "CSV file download simulation failed for Edge"


# todo: text AnkiConnect mocking it and checking for success message
# with allure.step("Verify success message"):
#     expected_message = "Successfully exported words to Anki."
#     success_message = page.wait_for_success_message(expected_message)
#     assert success_message is not None, f"Expected success message '{expected_message}' not found"
#     assert expected_message in success_message, f"Expected '{expected_message}', but got '{success_message}'"
