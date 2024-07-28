import pytest
from django.urls import reverse
import allure
from selenium.webdriver.common.by import By

from tests.conftest import USER_PASSWORD
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from tests.page_models.reader_page import ReaderPage


@allure.epic('End-to-end (selenium)')
@allure.feature('Reader')
@allure.story('Un-approved user cannot access reader view')
@pytest.mark.docker
@pytest.mark.selenium
@pytest.mark.django_db
def test_upapproved_user_cannot_access_reader_view(browser, user):
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
@allure.feature('Reader')
@allure.story('Reader view')
@pytest.mark.docker
@pytest.mark.selenium
@pytest.mark.django_db
def test_viewport_view_book(browser, approved_user, book):
    with allure.step("Login and navigate to reader"):
        browser.login(approved_user, USER_PASSWORD)
        browser.goto(reverse('reader') + f'?book-code={book.code}')
        reader_page = ReaderPage(browser)

    with allure.step("Verify page content is loaded"):
        page_content = reader_page.get_page_content()
        assert "Content of page 1" in page_content, "Expected content not found on the page"

    with allure.step("Click on a word and verify translation"):
        reader_page.click_word("page")

        try:
            translation = reader_page.wait_for_translation()
            assert translation is not None, "Translation span did not appear"

            translation_text = reader_page.get_translation()
            assert translation_text != "", "Translation is empty"

            allure.attach(
                browser.get_screenshot_as_png(),
                name='translation_screenshot',
                attachment_type=allure.attachment_type.PNG
            )
        except Exception as e:
            allure.attach(
                browser.get_screenshot_as_png(),
                name='translation_error_screenshot',
                attachment_type=allure.attachment_type.PNG
            )
            raise e

    browser.take_screenshot("Final")
