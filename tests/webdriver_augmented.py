import collections
from typing import Optional
import allure
import pytest
import requests
from django.urls import reverse
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
import time
import pprint
import urllib.parse
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


PAGE_MAX_WAIT_TIME = 20  # second to wait for components
PAGE_STEP_SLEEP = 0.5  # seconds to delay in component waiting loop
FIRST_PAGE_MAX_WAIT_TIME = 20  # seconds to wait for components on first page
MAX_JS_LOG_SIZE = 5 * 1024  # longer js log truncated in error messages


DjangoLiveServer = collections.namedtuple('DjangoLiveServer', ['docker_url', 'host_url'])


class PageTimer():
    """Count down timer для ожиданий с timeout.
    """
    first_page = True
    max_time = time.monotonic()# + FIRST_PAGE_MAX_WAIT_TIME

    def start(self):
        if self.first_page:
            self.max_time = time.monotonic() + FIRST_PAGE_MAX_WAIT_TIME
            self.first_page = False
        else:
            self.max_time = time.monotonic() + PAGE_MAX_WAIT_TIME

    def time_is_up(self):
        return time.monotonic() >= self.max_time

    def sleep(self):
        time.sleep(PAGE_STEP_SLEEP)

    def time_to_wait(self):
        return self.max_time - time.monotonic()


class Page:
    root = ''
    projects = 'projects'


class WebDriverAugmented(RemoteWebDriver):
    """
    Web driver, augmented with application specific logic.
    """
    def __init__(self, django_server: DjangoLiveServer, *args, **kwargs):
        self.page_timer = PageTimer()
        self.need_refresh = False
        self.host = django_server.docker_url
        self.host_outer = django_server.host_url
        super().__init__(*args, **kwargs)

    def login(self, user, password, wait_view="library", wait_seconds=3):
        """Perform the login process with the provided user credentials.

        Login redirect to reader, but no current book for the newly created user so redirect again to library.
        This is why the default we wait for "library" after login.
        """
        login_url = self.host + reverse('login')
        self.get(login_url)
    
        WebDriverWait(self, 10).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
    
        try:
            username_input = WebDriverWait(self, 10).until(
                EC.element_to_be_clickable((By.NAME, 'username'))
            )
            username_input.clear()
            username_input.send_keys(user.username)
            
            password_input = WebDriverWait(self, 10).until(
                EC.element_to_be_clickable((By.NAME, 'password'))
            )
            password_input.clear()
            password_input.send_keys(password)
    
            submit_button = WebDriverWait(self, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"]'))
            )
            submit_button.click()
    
            if wait_view:
                after_login_url = urllib.parse.urljoin(self.host, wait_view)
                WebDriverWait(self, wait_seconds).until(
                    EC.url_to_be(after_login_url),
                    message=f"Expected to be redirected to the {after_login_url} after login but stuck at {self.current_url}.",
                )
        except Exception as e:
            print(f"Login failed: {str(e)}")
            self.take_screenshot("login_failure")
            raise   
        
    def goto(self, page: str):
        """
        Open the page (see class Page).
        """
        url_host = urllib.parse.urljoin(self.host_outer, page)
        url_docker = urllib.parse.urljoin(self.host, page)
        print(f"Goto URL: from host {url_host}", f"from docker: {url_docker}")
        if requests.get(url_host).status_code != 200:
            raise AssertionError(
                f"Failed to get {url_host}: {requests.get(url_host).status_code}\n{requests.get(url_host).text}")
        self.get(urllib.parse.urljoin(self.host, page))

    def check_js_log(self):
        """
        Check JavaScript log for errors (only `severe` level).
        Fail the test if errors are found and attach the log to Allure.
        """
        if self.name.lower() == 'firefox':
            print("Skipping JavaScript log check for Firefox")
            return
        js_log = self.get_log("browser")
        severe_logs = []
        total_chars = 0
        for entry in js_log:
            if entry['level'] == 'SEVERE':
                if "Cross-Origin-Opener-Policy header has been ignored" in entry['message']:
                    continue
                severe_logs.append(entry)
                total_chars += len(entry['message'])
                if total_chars >= MAX_JS_LOG_SIZE:
                    severe_logs.append({'level': 'INFO', 'message': '<...>'})
                    break

        if severe_logs:
            log_text = '\n'.join([f"{entry['level']}: {entry['message']}" for entry in severe_logs])
            allure.attach(
                log_text,
                name='js critical errors',
                attachment_type=allure.attachment_type.TEXT
            )
            pytest.fail(f"JavaScript critical errors:\nSee the attached log in browser's `Tear down` for details")

    @property
    def visible_texts(self) -> str:
        """All visible text on the page."""
        visible_elements = self.find_elements(
            By.XPATH,
            "//*[not(self::script) and not(self::style) and normalize-space(.) != '']/parent::*"
        )
        return "".join([element.text for element in visible_elements if element.text.strip()])

    def get_errors_text(self, wait_seconds: Optional[int] = 3, no_errors_exception: bool = True) -> str:
        """All error text on the page.

        Wait for the error panels to appear if `wait_seconds` is not None.
        Raise TimeoutException if no error panel appear and `no_errors_exception`.
        """
        if wait_seconds is not None:
            WebDriverWait(self, wait_seconds).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".alert.alert-danger")),
                message="Expected error panels.",
            )

        error_panels = self.find_elements(By.CSS_SELECTOR, ".alert.alert-danger")
        if not error_panels and no_errors_exception:
            raise TimeoutException("No error panels found.")
        return "".join(panel.text for panel in error_panels if panel.text.strip())

    @property
    def errors_text(self) -> str:
        """All error text on the page.

        Wait for the error panels to appear.
        Raise TimeoutException if no error panel appear.
        """
        return self.get_errors_text()

    def take_screenshot(self, name: str = ''):
        """Take a screenshot and attach it to the allure report."""
        allure.attach(
            self.get_screenshot_as_png(),
            name=name,
            attachment_type=allure.attachment_type.PNG
        )

