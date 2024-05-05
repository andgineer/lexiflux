from time import sleep

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from django.urls import reverse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import allure
import requests
from tests.conftest import DjangoLiveServer


@pytest.mark.docker
@pytest.mark.selenium
@pytest.mark.django_db
def test_viewport_view_book(caplog, client, user, book, django_server: DjangoLiveServer, browser):
    client.force_login(user)
    url_host = django_server.host_url + reverse('reader') + f'?book-code={book.code}'
    url_docker = django_server.docker_url + reverse('reader') + f'?book-code={book.code}'
    print(f"URL from host: {url_host}", f"URL from docker: {url_docker}")
    if requests.get(url_host).status_code != 200:
        raise AssertionError(f"Failed to get {url_host}: {requests.get(url_host).status_code}\n{requests.get(url_host).text}")
    browser.get(url_docker)
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

