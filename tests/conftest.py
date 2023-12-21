import pytest
import os


os.environ["DJANGO_SETTINGS_MODULE"] = "core.settings"


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
    params=["Hello 123 <br/> word/123 123-<word>\n<br> and last!"]
)
def sentence_6_words(request):
    return request.param