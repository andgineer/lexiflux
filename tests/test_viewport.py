import pytest
from django.urls import reverse
import allure
from selenium.webdriver.common.by import By

from tests.conftest import USER_PASSWORD



@pytest.mark.docker
@pytest.mark.selenium
@pytest.mark.django_db
def test_viewport_view_book(caplog, client, approved_user, book, browser):
    browser.login(approved_user, USER_PASSWORD)

    browser.goto(reverse('reader') + f'?book-code={book.code}')

    allure.attach(
        browser.get_screenshot_as_png(),
        name='screenshot2',
        attachment_type=allure.attachment_type.PNG
    )

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

