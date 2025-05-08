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
            except Exception:
                if attempt == max_attempts - 1:
                    raise
                time.sleep(delay)

    def wait_for_element(self, locator, timeout=10):
        return WebDriverWait(self.browser, timeout).until(EC.presence_of_element_located(locator))

    def wait_for_clickable(self, locator, timeout=10):
        return WebDriverWait(self.browser, timeout).until(EC.element_to_be_clickable(locator))

    def wait_for_vue_updates(self):
        """Ensure Vue has processed all updates."""
        self.browser.execute_script("""
            return new Promise((resolve) => {
                Vue.nextTick(resolve);
            });
        """)

    def wait_for_htmx_loaded(self, timeout=10):
        """Wait for HTMX to be fully loaded on the page."""
        try:
            WebDriverWait(self.browser, timeout).until(
                lambda driver: driver.execute_script("return typeof htmx !== 'undefined'")
            )
            return True
        except Exception:
            return False

    def wait_for_htmx_requests_complete(self, timeout=10):
        """Wait for any HTMX requests to complete."""
        if not self.wait_for_htmx_loaded(timeout):
            # If HTMX isn't loaded after timeout, just wait a moment and continue
            self.browser.implicitly_wait(1)
            return

        try:
            WebDriverWait(self.browser, timeout).until(
                lambda driver: driver.execute_script("return !htmx.requesting")
            )
        except Exception:
            # If there's an issue checking the status, just wait a moment
            self.browser.implicitly_wait(1)
