"""Base page class."""
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class BasePage:
    def __init__(self, browser):
        self.browser = browser

    def retry_action(self, action, max_attempts=3, delay=1):
        for attempt in range(max_attempts):
            try:
                return action()
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise
                time.sleep(delay)

    def wait_for_element(self, locator, timeout=10):
        return WebDriverWait(self.browser, timeout).until(
            EC.presence_of_element_located(locator)
        )

    def wait_for_clickable(self, locator, timeout=10):
        return WebDriverWait(self.browser, timeout).until(
            EC.element_to_be_clickable(locator)
        )

    def wait_for_vue_updates(self):
        """ Ensure Vue has processed all updates."""
        self.browser.execute_script("""
            return new Promise((resolve) => {
                Vue.nextTick(resolve);
            });
        """)

