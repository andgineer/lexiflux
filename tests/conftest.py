import os
import platform
from datetime import timedelta

from ebooklib import epub, ITEM_DOCUMENT

from lexiflux.ebook.book_loader_epub import BookLoaderEpub
from lexiflux.language.google_languages import populate_languages

# Bind Django test server to all network interfaces so Selenium Hub could connect from Docker.
# For unknown reasons that does not work in pytest.ini so should be here
# https://github.com/pytest-dev/pytest-django/issues/300
# strange that DJANGO_SETTINGS_MODULE can be set in pytest.ini
os.environ["DJANGO_LIVE_TEST_SERVER_ADDRESS"] = "0.0.0.0"
os.environ["LEXIFLUX_SKIP_AUTH"] = "false"
os.environ["LEXIFLUX_ENV_NAME"] = "test"

import itertools
import socket
from urllib.parse import urlparse

import pytest
from unittest.mock import mock_open, patch, MagicMock

from lexiflux.ebook.book_loader_base import BookLoaderBase, MetadataField
from lexiflux.ebook.book_loader_plain_text import BookLoaderPlainText
from django.contrib.auth import get_user_model
import django.utils.timezone
from lexiflux.models import Author, Language, Book, BookPage, LanguageGroup, TranslationHistory, LanguagePreferences
from pytest_django.live_server_helper import LiveServer
import subprocess
import time
import allure
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.chrome.options import Options
from tests.webdriver_augmented import WebDriverAugmented, DjangoLiveServer
import urllib3.exceptions
import logging


log = logging.getLogger()

CHROME_BROWSER_NAME = 'Chrome'
FIREFOX_BROWSER_NAME = 'Firefox'
EDGE_BROWSER_NAME = 'Edge'

WEBDRIVER_HOST = 'http://localhost:4444/wd/hub'

test_browsers = [
    CHROME_BROWSER_NAME,
    FIREFOX_BROWSER_NAME,
    EDGE_BROWSER_NAME,
]
browser_options = {
    CHROME_BROWSER_NAME: ChromeOptions,
    FIREFOX_BROWSER_NAME: FirefoxOptions,
    EDGE_BROWSER_NAME: EdgeOptions,
}



def pytest_addoption(parser):
    parser.addoption(
        "--use-llm",
        action="store_true",
        help="Use real LLM (chatGPT) so tests will spend money",
    )


def is_docker_compose_running(service_name: str) -> bool:
    """Check if any Selenium Hub is running by checking port 4444."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', 4444)) == 0
    except Exception as e:
        print(f"Failed to check Selenium Hub status: {e}")
        return False


def start_docker_compose():
    """Starts the docker-compose services and logs output directly."""
    try:
        result = subprocess.run(
            ["docker", "compose", "up", "-d"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        print("Docker Compose started successfully.")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Failed to start Docker Compose.")
        print(e.stdout)
        print(e.stderr)
        raise RuntimeError("Docker Compose failed to start") from e


@pytest.fixture(scope="session")
def with_selenium():
    """Start Selenium Grid using Testcontainers if not already running."""
    service_name = "hub"
    if not is_docker_compose_running(service_name):
        start_docker_compose()
    yield


def get_options(browser: str) -> Options:
    options = browser_options[browser]()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument("--disable-client-side-phishing-detection")
    options.add_argument("--no-sandbox")
    options.add_argument('--headless')
    return options


def get_web_driver(browser_name: str, django_server: DjangoLiveServer, retry_interval=2, timeout=60) -> WebDriverAugmented:
    """
    Creates remote web driver (located on selenium host) for desired browser.
    """
    FAIL_HELP = f'''
    Fail to connect to selenium webdriver remote host {WEBDRIVER_HOST}.

    To run local selenium hub from tests_e2e folder: 
        docker compose up -d
    '''
    end_time = time.time() + timeout
    while True:
        try:
            webdrv = WebDriverAugmented(
                django_server=django_server,
                command_executor=WEBDRIVER_HOST,
                options=get_options(browser_name),
            )
            webdrv.browser_name = browser_name
            webdrv.page_timer.start()
            return webdrv
        except urllib3.exceptions.ProtocolError as e:
            if time.time() >= end_time:
                pytest.exit(f'{FAIL_HELP}\n\n{e}\n')
            print(f"Connection failed: {e}. Retrying in {retry_interval} seconds...")
            time.sleep(retry_interval)
        except WebDriverException as e:
            pytest.exit(f'{FAIL_HELP}:\n\n{e}\n')
        except (urllib3.exceptions.ReadTimeoutError, urllib3.exceptions.NewConnectionError, urllib3.exceptions.MaxRetryError) as e:
            pytest.exit(f'{FAIL_HELP}:\n\n{e}\n')


@pytest.fixture(scope='function', params=test_browsers, ids=lambda x: f'Browser: {x}')
def browser(request, with_selenium, django_server: DjangoLiveServer) -> WebDriverAugmented:
    """
    Returns all browsers to test with
    """
    webdrv = get_web_driver(request.param, django_server)
    request.addfinalizer(lambda *args: webdrv.quit())
    # driver.implicitly_wait(Config().WEB_DRIVER_IMPLICITE_WAIT)
    webdrv.maximize_window()
    yield webdrv
    webdrv.check_js_log()


def get_docker_host_ip():
    """Get the IP address of the host accessible from within Docker containers.

    So we can test servers running on the host machine from the Selenium Hub.
    """
    if platform.system() == "Darwin":
        return "host.docker.internal"
    elif platform.system() == "Linux":
        return get_linux_docker_host_ip()
    else:
        raise RuntimeError("Unsupported platform")


def get_linux_docker_host_ip():
    """ Determine the IP address accessible from within Docker containers on Linux.

    Get the default gateway address.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 1))  # Use a temporary connection to an external IP
            host_ip = s.getsockname()[0]
        return host_ip
    except socket.error as e:
        raise RuntimeError(f"Failed to determine host IP address: {e}") from e


@pytest.fixture
def django_server(live_server: LiveServer) -> DjangoLiveServer:
    port = urlparse(live_server.url).port
    yield DjangoLiveServer(
        docker_url=f"http://{get_docker_host_ip()}:{port}",
        host_url=f"http://0.0.0.0:{port}"
    )


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == 'call' and rep.failed:
        try:
            if 'browser' in item.fixturenames:  # assume this is fixture with webdriver
                web_driver = item.funcargs['browser']
            else:
                return
            allure.attach(
                web_driver.get_screenshot_as_png(),
                name='post-mortem screenshot',
                attachment_type=allure.attachment_type.PNG
            )
            if web_driver.browser_name != FIREFOX_BROWSER_NAME:
                # Firefox do not support js logs: https://github.com/SeleniumHQ/selenium/issues/2972
                js_logs = web_driver.get_log('browser')
                log_entries = [f"{entry['level']}: {entry['message']}" for entry in js_logs]
                allure.attach(
                    '\n'.join(log_entries),
                    name='js console log:',
                    attachment_type=allure.attachment_type.TEXT,
                )

        except Exception as e:
            print(f'Fail to attach browser artifacts: {e}')


@pytest.fixture(
    scope="function",
    params=[
        "\n\nCHAPTER VII.\nA Mad Tea-Party\n\n",
        "\n\nCHAPTER I\n\n",
        "\n\nCHAPTER Two\n\n",
        "\n\nCHAPTER Third\n\n",
        "\n\nCHAPTER four. FALL\n\n",
        "\n\nCHAPTER twenty two. WINTER\n\n",
        "\n\nCHAPTER last inline\nunderline\n\n",
        "\n\nI. A SCANDAL IN BOHEMIA\n \n",
        "\n\nV.\nПет наранчиних сjеменки\n\n",
    ],)
def chapter_pattern(request):
    return request.param


@pytest.fixture(
    scope="function",
    params=[
        "\ncorrespondent could be.\n\n",
    ],)
def wrong_chapter_pattern(request):
    return request.param


@pytest.fixture(
    scope="function",
    params=["Hello 123 <br/> word/123 123-<word>\n<br/> and last!"]
)
def sentence_6_words(request):
    return request.param


@pytest.fixture
def book_plain_text():
    # Create a sample data string
    sample_data = " ".join([f"Word{i}" for i in range(1, 1000)])

    # Convert sample data to bytes with an encoding, e.g., UTF-8
    sample_data_bytes = sample_data.encode('utf-8')

    # Custom mock open function to handle different modes
    def custom_open(file, mode='r', encoding=None):
        if 'b' in mode:
            return mock_open(read_data=sample_data_bytes).return_value
        else:
            # Decode the data if a specific encoding is provided
            decoded_data = sample_data_bytes.decode(encoding)
            return mock_open(read_data=decoded_data).return_value

    with patch("builtins.open", new_callable=lambda: custom_open):
        return BookLoaderPlainText("dummy_path")


@pytest.fixture
def book_epub(db_init):
    # Create a mock EPUB book
    mock_book = MagicMock(spec=epub.EpubBook)

    # Create mock EPUB items (pages)
    mock_items = [
        MagicMock(spec=epub.EpubHtml,
                  get_body_content=lambda: (f"Page {i} " + " ".join([f'word{j}' for j in range(200)])).encode('utf-8'),
                  get_type=lambda: ITEM_DOCUMENT,
                  file_name=f"page_{i}.xhtml",
                  get_name=lambda: f"page_{i}.xhtml",
                  get_id=lambda: f'item_{i}',
                  )
        for i in range(20)  # 20 pages
    ]

    # Set up the mock book to return our mock items
    mock_book.get_items.return_value = mock_items
    mock_book.spine = [(f'item_{i}',) for i in range(len(mock_items))]
    mock_book.get_item_with_id = lambda id: mock_items[int(id.split('_')[1])]

    # Mock the toc attribute
    mock_book.toc = [MagicMock(spec=epub.Link, title=f"Chapter {i}", href=f"page_{i}.xhtml") for i in range(5)]

    # Mock other necessary attributes and methods
    mock_book.get_metadata.return_value = [('', 'Sample Title')]

    # Patch epub.read_epub to return our mock book
    with patch('ebooklib.epub.read_epub', return_value=mock_book):
        loader = BookLoaderEpub("dummy_path")
        loader.detect_meta()  # This will set up the epub attribute
        return loader


@pytest.fixture(autouse=True)
def mock_detect_language():
    mock_detector = MagicMock()
    mock_detector.detect.side_effect = itertools.cycle(['en', 'en', 'fr'])

    with patch('lexiflux.ebook.book_loader_base.language_detector', return_value=mock_detector):
        yield mock_detector.detect


@pytest.fixture
def book_processor_mock(db_init):
    """Fixture to create a real BookLoaderBase instance with mocked detect_language."""
    class TestBookLoader(BookLoaderBase):
        def detect_meta(self):
            return {
                MetadataField.TITLE: 'Test Book',
                MetadataField.AUTHOR: 'Test Author',
                MetadataField.LANGUAGE: 'English'
            }, 0, 100

        def get_random_words(self, words_num=15):
            return "Sample random words for language detection"

        def pages(self):
            yield "Page 1 content"
            yield "Page 2 content"

    with patch.object(BookLoaderBase, 'detect_language', return_value='English'):
        book_processor = TestBookLoader('dummy_path')
        return book_processor


USER_PASSWORD = '12345'


@pytest.fixture
def db_init(db):
    """Fixture to populate the database with languages."""
    populate_languages()


@pytest.fixture
def user(db_init):
    return get_user_model().objects.create_user(username='testuser', password=USER_PASSWORD)


@pytest.fixture
def approved_user(user, language):
    user.is_approved = True
    user.language = language
    user.save()
    return user


@pytest.fixture
def author(db_init):
    return Author.objects.create(name="Lewis Carroll")


@pytest.fixture
def book(db_init, user, author):
    language = Language.objects.get(name="English")
    book = Book.objects.create(
        title="Alice in Wonderland",
        author=author,
        language=language,
        code='some-book-code',
        owner=user
    )

    for i in range(1, 6):
        BookPage.objects.create(
            book=book,
            number=i,
            content=f"Content of page {i}"
        )

    return book


@pytest.fixture
def translation_history(book, approved_user, language):
    return TranslationHistory.objects.create(
        user=approved_user,
        book=book,
        term='apple',
        translation='pomme',
        context=f'{TranslationHistory.CONTEXT_MARK}before__{TranslationHistory.CONTEXT_MARK}__after{TranslationHistory.CONTEXT_MARK}',
        source_language=language,
        target_language=language,
        first_lookup=django.utils.timezone.now() - timedelta(minutes=1),
    )


@pytest.fixture
def language(db_init):
    return Language.objects.get(name="English")


@pytest.fixture
def language_group(db_init):
    group = LanguageGroup.objects.create(name="Test Group")
    group.languages.add(Language.objects.get(name="English"))
    group.languages.add(Language.objects.get(name="French"))
    return group


@pytest.fixture
def user_with_translations(approved_user, book, language, translation_history):
    user_language, _ = Language.objects.get_or_create(name="User Language", google_code="ul")
    language_preferences = LanguagePreferences.objects.create(
        user=approved_user,
        language=language,
        user_language=user_language,
        inline_translation_type='Translate',
        inline_translation_parameters={'model': 'default_model'}
    )
    approved_user.default_language_preferences = language_preferences
    approved_user.save()
    return approved_user


@pytest.fixture
def book_epub_loader(db_init):
    return BookLoaderEpub("tests/resources/genius.epub")