from unittest.mock import patch, MagicMock

import pytest
from django.urls import reverse
import allure

from tests.conftest import USER_PASSWORD
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from tests.page_models.reader_page import ReaderPage


@allure.epic('End-to-end (selenium)')
@allure.feature('Reader page')
@allure.story('Un-approved user cannot access reader page')
@pytest.mark.docker
@pytest.mark.selenium
@pytest.mark.django_db
def test_e2e_reader_page_upapproved_user_cannot_access(browser, user):
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



def mock_translate(text):
    return "Mocked translation of: " + text

def mock_generate_article(**kwargs):
    return "Mocked article content"


@allure.epic('End-to-end (selenium)')
@allure.feature('Reader page')
@allure.story('Click to translate')
@pytest.mark.docker
@pytest.mark.selenium
@pytest.mark.django_db
@patch('lexiflux.views.lexical_views.get_translator')
@patch('lexiflux.views.lexical_views.Llm')
def test_e2e_reader_page_click_to_translate(mock_llm, mock_get_translator, browser, approved_user, book):
    mock_translator = MagicMock()
    mock_translator.translate.side_effect = mock_translate
    mock_get_translator.return_value = mock_translator

    mock_llm_instance = MagicMock()
    mock_llm_instance.generate_article.side_effect = mock_generate_article
    mock_llm_instance.mark_term_and_sentence.return_value = "Mocked marked text"
    mock_llm.return_value = mock_llm_instance

    with allure.step("Login and navigate to reader"):
        browser.login(approved_user, USER_PASSWORD)
        browser.goto(reverse('reader') + f'?book-code={book.code}')
        reader_page = ReaderPage(browser)

    with allure.step("Verify page content is loaded"):
        page_content = reader_page.get_page_content()
        allure.attach(page_content, name="Page Content", attachment_type=allure.attachment_type.TEXT)
        assert "Content of page 1" in page_content, f"Expected content not found. Actual content: {page_content}"

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
