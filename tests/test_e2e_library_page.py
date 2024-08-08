import pytest
import allure
from django.urls import reverse
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from tests.conftest import USER_PASSWORD
from tests.page_models.library_page import LibraryPage


@allure.epic('End-to-end (selenium)')
@allure.feature('Library Page')
@allure.story('Un-approved user cannot access library page')
@pytest.mark.docker
@pytest.mark.selenium
@pytest.mark.django_db
def test_e2e_library_page_upapproved_user_cannot_access(browser, user):
    browser.login(user, USER_PASSWORD, wait_view=None)
    WebDriverWait(browser, 3).until(
        EC.url_to_be(browser.host + reverse('login')),  # raise TimeoutException if not
        message="Expected to be redirected to login page again after login with unapproved user.",
    )
    assert "Your account is not approved yet." in browser.errors_text

    # just to be sure
    allure.attach(
        browser.get_screenshot_as_png(),
        name='after_unapproved_login_screenshot',
        attachment_type=allure.attachment_type.PNG
    )


@allure.epic('End-to-end (selenium)')
@allure.feature('Library Page')
@allure.story('Book Editing')
@pytest.mark.docker
@pytest.mark.selenium
@pytest.mark.django_db
def test_e2e_library_page_edit_book(browser, approved_user, book):
    with allure.step("Login and navigate to library page"):
        browser.login(approved_user, USER_PASSWORD)
        page = LibraryPage(browser)
        page.goto()
        browser.take_screenshot("Initial Library Page")

    with allure.step("Verify initial page state"):
        assert "Your Books" in page.get_page_title()

    with allure.step("Get the title and author of the first book"):
        initial_title, initial_author = page.get_first_book_info()
        assert initial_title, "No books found in the library"

    with allure.step("Open edit modal for the first book"):
        page.open_edit_modal_for_first_book()
        browser.take_screenshot("Edit Book Modal")

    with allure.step("Verify correct title and author in edit dialog"):
        dialog_title, dialog_author = page.get_edit_dialog_info()
        assert dialog_title == initial_title, f"Expected title '{initial_title}', but got '{dialog_title}' in edit dialog"
        assert dialog_author == initial_author, f"Expected author '{initial_author}', but got '{dialog_author}' in edit dialog"

    new_title = f"Updated: {initial_title}"
    new_author = f"Updated: {initial_author}"
    with allure.step(f"Change book title to '{new_title}' and author to '{new_author}' and save"):
        page.edit_book_title(new_title)
        page.edit_book_author(new_author)
        page.save_book_changes()
        browser.take_screenshot("After Saving Changes")

    with allure.step("Verify the book title and author have been updated"):
        updated_title, updated_author = page.get_first_book_info()
        assert updated_title == new_title, f"Expected title '{new_title}', but got '{updated_title}'"
        assert updated_author == new_author, f"Expected author '{new_author}', but got '{updated_author}'"

    browser.take_screenshot("Final Library Page")