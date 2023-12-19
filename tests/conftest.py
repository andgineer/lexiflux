import pytest


@pytest.fixture(
    scope="function",
    params=[
        "\nCHAPTER VII.\nA Mad Tea-Party\n\n",
        "\nCHAPTER I\n\n",
        "\nCHAPTER Two\n\n",
        "\nCHAPTER Third\n\n",
        "\nCHAPTER four. FALL\n\n",
        "\nI. A SCANDAL IN BOHEMIA\n \n",
        "\nV. \nThe Five Orange Pips\n\n",
    ],)
def chapter_pattern(request):
    return request.param
