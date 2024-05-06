import pytest
from django.urls import reverse
import allure
from selenium.webdriver.common.by import By

from tests.conftest import USER_PASSWORD
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
def test_viewport_view_book(browser, approved_user, caplog, client, book):
    browser.login(approved_user, USER_PASSWORD)

    browser.goto(reverse('reader') + f'?book-code={book.code}')

    allure.attach(
        browser.get_screenshot_as_png(),
        name='reader_screenshot',
        attachment_type=allure.attachment_type.PNG
    )

    assert browser.get_errors_text(no_errors_exception=False, wait_seconds=None) == ""

    # # Test book page scrolling
    # book_page_scroller = WebDriverWait(browser, 10).until(
    #     EC.presence_of_element_located((By.ID, 'book-page-scroller'))
    # )
    # assert book_page_scroller.text.startswith('This is the first page.')
    #
    # # Scroll to the next page
    # browser.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", book_page_scroller)
    # WebDriverWait(browser, 10).until(
    #     EC.text_to_be_present_in_element((By.ID, 'book-page-scroller'), 'This is the second page.')
    # )

