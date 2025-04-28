import logging
import pytest
import allure

from selenium.webdriver.common.by import By

from tests.conftest import USER_PASSWORD
from tests.page_models.library_page import LibraryPage
from tests.page_models.import_modal_page import ImportModalPage


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
