import collections

import requests
from django.urls import reverse
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
import time
import pprint
import urllib.parse


PAGE_MAX_WAIT_TIME = 20  # second to wait for components
PAGE_STEP_SLEEP = 0.5  # seconds to delay in component waiting loop
FIRST_PAGE_MAX_WAIT_TIME = 20  # seconds to wait for components on first page
MAX_JS_LOG_SIZE = 1024  # longer js log truncated in error messages


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

    def login(self, user, password):
        """
        Perform the login process with the provided user credentials.
        """
        login_url = self.host + reverse('login')
        self.get(login_url)

        username_input = self.find_element(By.NAME, 'username')
        password_input = self.find_element(By.NAME, 'password')

        username_input.send_keys(user.username)
        password_input.send_keys(password)
        password_input.submit()

    def goto(self, page: str):
        """
        Open the page (see class Page).
        """
        url_host = self.host_outer + page
        url_docker = self.host + page
        print(f"Goto URL: from host {url_host}", f"from docker: {url_docker}")
        if requests.get(url_host).status_code != 200:
            raise AssertionError(
                f"Failed to get {url_host}: {requests.get(url_host).status_code}\n{requests.get(url_host).text}")
        self.get(urllib.parse.urljoin(self.host, page))

    def check_js_log(self):
        """
        check java script log for errors (only `severe` level)
        """
        js_log = self.get_log("browser")
        clean_log = []
        total_chars = 0
        idx = 0
        for entry in js_log:
            if entry['level'] in ['SEVERE']:
                idx += 1
                clean_log.append(entry)
                total_chars += len(entry['message'])
                if total_chars >= MAX_JS_LOG_SIZE:
                    clean_log.append('<...>')
                    break
        assert not clean_log, 'js log errors: \n{}'.format(
            pprint.pformat(clean_log, indent=4)
        )

