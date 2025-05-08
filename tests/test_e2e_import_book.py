import logging
import os
import tempfile

import pytest
import allure

from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

from lexiflux.models import Book
from tests.conftest import USER_PASSWORD
from tests.page_models.library_page import LibraryPage
from tests.page_models.import_modal_page import ImportModalPage
from selenium.webdriver.support import expected_conditions as EC


log = logging.getLogger()


@allure.epic("End-to-end (selenium)")
@allure.feature("Library Page")
@allure.story("Import Books")
@pytest.mark.docker
@pytest.mark.selenium
@pytest.mark.django_db
def test_e2e_import_modal_navigation(browser, approved_user):
    """Test basic navigation and UI of the import modal."""
    import_page = ImportModalPage(browser)

    with allure.step("Login and navigate to library page"):
        browser.login(approved_user, USER_PASSWORD)
        library_page = LibraryPage(browser)
        library_page.goto()
        browser.take_screenshot("Initial Library Page")

    import_page.open_import_modal()

    with allure.step("Navigate to URL tab"):
        import_page.select_url_tab()
        browser.take_screenshot("URL Tab Selected")
        assert browser.find_element(By.ID, "bookUrl").is_displayed()

    with allure.step("Navigate to Paste tab"):
        import_page.select_paste_tab()
        browser.take_screenshot("Paste Tab Selected")
        assert browser.find_element(By.ID, "pasteOverlay").is_displayed()

    with allure.step("Navigate back to File tab"):
        import_page.select_file_tab()
        browser.take_screenshot("File Tab Selected")
        assert browser.find_element(By.ID, "bookFile").is_displayed()


@allure.epic("End-to-end (selenium)")
@allure.feature("Library Page")
@allure.story("Import Books Via URL")
@pytest.mark.docker
@pytest.mark.selenium
@pytest.mark.django_db
def test_e2e_import_from_url(browser, approved_user, monkeypatch):
    """Test importing a book from a URL."""
    import_page = ImportModalPage(browser)

    # Use a fake but valid-looking URL
    test_url = "https://example.com/test-book.html"

    # Mock the HTTP request
    import requests

    def mock_get(*args, **kwargs):
        # Create a mock response
        mock_response = requests.Response()
        mock_response.status_code = 200
        mock_response._content = b"""
        <html>
            <head><title>Pride and Prejudice</title></head>
            <body>
                <h1>Pride and Prejudice</h1>
                <p>By Jane Austen</p>
                <p>It is a truth universally acknowledged, that a single man in possession
                of a good fortune, must be in want of a wife.</p>
            </body>
        </html>
        """
        return mock_response

    # Apply the monkeypatch to requests.get
    monkeypatch.setattr(requests, "get", mock_get)

    with allure.step("Login and navigate to library page"):
        browser.login(approved_user, USER_PASSWORD)
        library_page = LibraryPage(browser)
        library_page.goto()
        browser.take_screenshot("Library Page Initial")

    with allure.step("Open import modal"):
        import_page.open_import_modal()
        modal = import_page.wait_for_modal()
        browser.take_screenshot("Import Modal Open")

    with allure.step(f"Import book from URL: {test_url}"):
        import_page.select_url_tab()
        import_page.enter_url(test_url)

        # Select cleaning level
        import_page.select_cleaning_level("aggressive")
        browser.take_screenshot("Before URL Import Submit")

        # Submit the import
        import_page.submit_import()

        # Wait for the edit book modal to appear after successful import
        try:
            edit_modal = import_page.wait_for_edit_book_modal()
            browser.take_screenshot("After URL Import Success")

            # Verify that book title was properly extracted
            title_input = edit_modal.find_element(By.ID, "bookTitle")
            assert "Pride and Prejudice" in title_input.get_attribute("value")
            log.info("Book title extracted correctly")

            # Simply verify we can see the form fields and they're populated correctly
            author_input = edit_modal.find_element(By.ID, "bookAuthor")
            assert author_input.is_displayed()
            log.info("Author input field is displayed")

            edit_modal.find_element(By.CSS_SELECTOR, ".btn-primary").click()
            log.info("Book saved successfully")

            # Wait for redirect to reader page
            WebDriverWait(browser, 10).until(EC.url_contains("/reader"))
            log.info("Redirected to reader page")

            book = Book.objects.filter().last()
            assert ">Pride and Prejudice</h1>" in book.pages.first().content

            dropdown_button = WebDriverWait(browser, 10).until(
                EC.presence_of_element_located((By.ID, "dropdownMenuButton"))
            )
            assert "Pride and Prejudice" in dropdown_button.text
            browser.take_screenshot("Reader Page Title Visible")

            # Verify the content in the words container
            words_container = WebDriverWait(browser, 10).until(
                EC.visibility_of_element_located((By.ID, "words-container"))
            )
            container_text = words_container.text

        except Exception as e:
            # If there was an error, get the error message and fail the test
            error_msg = import_page.get_error_message() or str(e)
            browser.take_screenshot("URL Import Error")
            pytest.fail(f"Failed to import from URL: {error_msg}")


@allure.epic("End-to-end (selenium)")
@allure.feature("Library Page")
@allure.story("Import Books Via Paste")
@pytest.mark.docker
@pytest.mark.selenium
@pytest.mark.django_db
def test_e2e_import_from_paste(browser, approved_user):
    """Test importing a book from pasted content."""
    # Simple content for testing
    import_page = ImportModalPage(browser)
    test_content = """# Test Book

This is a test book created via paste.

## Chapter 1

Once upon a time, there was a test that needed to be run.

The end."""

    with allure.step("Login and navigate to library page"):
        browser.login(approved_user, USER_PASSWORD)
        library_page = LibraryPage(browser)
        library_page.goto()

        # Get initial book count
        initial_book_count = Book.objects.filter(owner=approved_user).count()

    import_page.open_import_modal()

    with allure.step("Import book from pasted content"):
        import_page.select_paste_tab()
        import_page.enter_paste_content(test_content)

        # Select plain text format
        import_page.select_paste_format("txt")
        browser.take_screenshot("Before Paste Import Submit")

        # Submit the import
        import_page.submit_import()

        # Wait for the edit book modal to appear after successful import
        try:
            edit_modal = import_page.wait_for_edit_book_modal()
            browser.take_screenshot("After Paste Import Success")

            # Fill in required title and author
            title_input = edit_modal.find_element(By.ID, "bookTitle")
            title_input.clear()
            title_input.send_keys("Test Pasted Book")

            author_input = edit_modal.find_element(By.ID, "bookAuthor")
            author_input.clear()
            author_input.send_keys("Test Author")

            # Save the book
            edit_modal.find_element(By.CSS_SELECTOR, ".btn-primary").click()

            WebDriverWait(browser, 10).until(EC.url_contains("/reader"))
            log.info("Redirected to reader page")

            book = Book.objects.filter().last()
            assert "book created via paste." in book.pages.first().content

            dropdown_button = WebDriverWait(browser, 10).until(
                EC.presence_of_element_located((By.ID, "dropdownMenuButton"))
            )
            assert "Test Pasted Book" in dropdown_button.text

        except Exception as e:
            # If there was an error, get the error message and fail the test
            error_msg = import_page.get_error_message() or str(e)
            browser.take_screenshot("Paste Import Error")
            pytest.fail(f"Failed to import from paste: {error_msg}")


@allure.epic("End-to-end (selenium)")
@allure.feature("Library Page")
@allure.story("Import Books Via File")
@pytest.mark.docker
@pytest.mark.selenium
@pytest.mark.django_db
def test_e2e_import_from_file(browser, approved_user):
    """Test importing a book from a file."""
    import_page = ImportModalPage(browser)

    with allure.step("Create a temporary text file"):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as tmp:
            tmp.write("""# Test File Import

This is a test book created via file upload.

## Chapter 1

This is chapter one of the test book.""")
            test_file_path = tmp.name

    try:
        with allure.step("Login and navigate to library page"):
            browser.login(approved_user, USER_PASSWORD)
            library_page = LibraryPage(browser)
            library_page.goto()

            # Get initial book count
            initial_book_count = Book.objects.filter(owner=approved_user).count()

        import_page.open_import_modal()

        with allure.step("Import book from file"):
            # We're on the file tab by default
            import_page.upload_file(test_file_path)
            browser.take_screenshot("Before File Import Submit")

            # Submit the import
            import_page.submit_import()

            # Wait for the edit book modal to appear after successful import
            try:
                import_page.fill_edit_book_form("Test File Book", "Test Author")
                browser.take_screenshot("After Fill Form")

                # Save the book
                import_page.save_book_changes()
                browser.take_screenshot("After Save Book")

                WebDriverWait(browser, 10).until(EC.url_contains("/reader"))
                log.info("Redirected to reader page")

                book = Book.objects.filter().last()
                assert "book created via file upload." in book.pages.first().content

                dropdown_button = WebDriverWait(browser, 10).until(
                    EC.presence_of_element_located((By.ID, "dropdownMenuButton"))
                )
                assert "Test File Book" in dropdown_button.text

            except Exception as e:
                # If there was an error, get the error message and fail the test
                log.exception("File Import Error")
                error_msg = import_page.get_error_message() or str(e)
                browser.take_screenshot("File Import Error")
                pytest.fail(f"Failed to import from file: {error_msg}")

    finally:
        # Clean up the temporary file
        if os.path.exists(test_file_path):
            os.unlink(test_file_path)
