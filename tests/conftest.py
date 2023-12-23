import itertools

import pytest
import os
from unittest.mock import mock_open, patch
from lexiflux.ebook.book_plain_text import BookPlainText


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
        return BookPlainText("dummy_path")


@pytest.fixture(autouse=True)
def mock_detect_language():
    with patch('lexiflux.language.translation.single_detection') as mock:
        mock.side_effect = itertools.cycle(['en', 'en', 'fr'])
        with patch.dict(os.environ, {"DETECTLANGUAGE_API_KEY": 'fake-key'}):
            yield mock

