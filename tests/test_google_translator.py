import json
import time
from unittest.mock import patch

import allure
import httpx
import pytest
from django.urls import reverse

from lexiflux.language.translation import (
    GOOGLE_CLIENTS,
    GOOGLE_TIMEOUT_SECONDS,
    GoogleTranslation,
    GoogleTranslator,
    Term,
    Translator,
    TranslatorError,
    google_code,
    parse_google_answer,
)
from lexiflux.models import LanguagePreferences, LexicalArticle, TranslationHistory

SPRING_NOUNS = [
    "весна",
    "пружина",
    "рессора",
    "источник",
    "родник",
    "ключ",
    "упругость",
    "прыжок",
    "начало",
    "мотив",
]
SPRING = [
    [["весна", "spring", None, None, 10]],
    [
        ["noun", SPRING_NOUNS, [["весна", ["spring", "springtime"], None, 0.17]], "spring", 1],
        ["verb", ["возникать", "пружинить"], [["возникать", ["arise"], None, 0.01]], "spring", 2],
    ],
    "en",
    None,
    None,
    None,
    None,
    [],
]
GRAD = [[["город", "град", None, None, 11]], None, "sr", None, None, None, None, []]
SORRY_PAGE = "<html><title>Sorry...</title></html>"


class GoogleEndpoint:
    def __init__(self, *answers):
        self.answers = list(answers)
        self.requests: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        if isinstance(answer, httpx.Response):
            return answer
        return httpx.Response(200, json=answer)

    @property
    def clients(self) -> list[str]:
        return [request.url.params["client"] for request in self.requests]


def _translator(endpoint, source="en", target="ru"):
    return GoogleTranslator(source, target, transport=httpx.MockTransport(endpoint.handle))


@allure.epic("Translators")
@allure.feature("Google")
def test_google_request_asks_for_translation_and_dictionary():
    endpoint = GoogleEndpoint(SPRING)

    _translator(endpoint).lookup("spring")

    (request,) = endpoint.requests
    assert f"{request.url.scheme}://{request.url.host}{request.url.path}" == (
        "https://translate.googleapis.com/translate_a/single"
    )
    params = request.url.params
    assert params["client"] == "dict-chrome-ex"
    assert (params["sl"], params["tl"], params["q"]) == ("en", "ru", "spring")
    assert params.get_list("dt") == ["t", "bd"]


@allure.epic("Translators")
@allure.feature("Google")
def test_google_timeout_is_three_seconds_for_the_whole_lookup():
    endpoint = GoogleEndpoint(httpx.Response(429, text=SORRY_PAGE), SPRING)

    _translator(endpoint).lookup("spring")

    first, second = (request.extensions["timeout"]["read"] for request in endpoint.requests)
    assert GOOGLE_TIMEOUT_SECONDS == 3.0
    assert 2.5 < first <= 3.0
    assert second <= first


@allure.epic("Translators")
@allure.feature("Google")
def test_google_tries_no_identifier_after_the_time_is_up():
    endpoint = GoogleEndpoint(httpx.Response(429, text=SORRY_PAGE), SPRING)

    def slow(request):
        time.sleep(0.3)
        return endpoint.handle(request)

    with patch("lexiflux.language.translation.GOOGLE_TIMEOUT_SECONDS", 0.2):
        translator = GoogleTranslator("en", "ru", transport=httpx.MockTransport(slow))
        with pytest.raises(TranslatorError) as error:
            translator.lookup("spring")

    assert error.value.kind == TranslatorError.RATE_LIMIT
    assert endpoint.clients == ["dict-chrome-ex"]


@allure.epic("Translators")
@allure.feature("Google")
@pytest.mark.parametrize(
    "refusal",
    [
        pytest.param(httpx.Response(429, text=SORRY_PAGE), id="429"),
        pytest.param(httpx.Response(403, text=SORRY_PAGE), id="403"),
        pytest.param(httpx.Response(200, text=SORRY_PAGE), id="non-json"),
        pytest.param(httpx.Response(302, headers={"Location": "/sorry"}), id="redirect"),
    ],
)
def test_google_refused_identifier_moves_on_to_the_next(refusal):
    endpoint = GoogleEndpoint(refusal, SPRING)

    result = _translator(endpoint).lookup("spring")

    assert endpoint.clients == ["dict-chrome-ex", "gtx"]
    assert result.translation == "весна"


@allure.epic("Translators")
@allure.feature("Google")
def test_google_identifiers_are_tried_in_order():
    endpoint = GoogleEndpoint(
        httpx.Response(429, text=SORRY_PAGE),
        httpx.Response(403, text=SORRY_PAGE),
        GRAD,
    )

    assert _translator(endpoint, "sr").translate(Term("град")) == "город"
    assert endpoint.clients == ["dict-chrome-ex", "gtx", "at"]
    assert tuple(endpoint.clients) == GOOGLE_CLIENTS


@allure.epic("Translators")
@allure.feature("Google")
def test_google_every_identifier_refused_is_a_rate_limit():
    endpoint = GoogleEndpoint(
        httpx.Response(429, text=SORRY_PAGE),
        httpx.Response(200, text=SORRY_PAGE),
        httpx.Response(403, text=SORRY_PAGE),
    )

    with pytest.raises(TranslatorError) as error:
        _translator(endpoint).lookup("spring")

    assert error.value.kind == TranslatorError.RATE_LIMIT
    assert endpoint.clients == list(GOOGLE_CLIENTS)


@allure.epic("Translators")
@allure.feature("Google")
@pytest.mark.parametrize(
    "failure",
    [
        pytest.param(httpx.ConnectError("refused"), id="connect"),
        pytest.param(httpx.ReadTimeout("slow"), id="timeout"),
        pytest.param(httpx.Response(500, text="oops"), id="server-error"),
        pytest.param(httpx.Response(400, text="bad"), id="bad-request"),
    ],
)
def test_google_network_failure_does_not_try_other_identifiers(failure):
    endpoint = GoogleEndpoint(failure, SPRING)

    with pytest.raises(TranslatorError) as error:
        _translator(endpoint).lookup("spring")

    assert error.value.kind == TranslatorError.NETWORK
    assert endpoint.clients == ["dict-chrome-ex"]


@allure.epic("Translators")
@allure.feature("Google")
def test_google_alternatives_grouped_by_part_of_speech():
    result = _translator(GoogleEndpoint(SPRING)).lookup("spring")

    assert result == GoogleTranslation(
        "весна",
        (("noun", tuple(SPRING_NOUNS[:8])), ("verb", ("возникать", "пружинить"))),
    )
    assert result.text() == (
        "весна\n"
        "*noun:* весна, пружина, рессора, источник, родник, ключ, упругость, прыжок\n"
        "*verb:* возникать, пружинить"
    )


@allure.epic("Translators")
@allure.feature("Google")
def test_google_without_dictionary_data_is_the_translation_only():
    result = _translator(GoogleEndpoint(GRAD), "sr").lookup("град")

    assert result == GoogleTranslation("город")
    assert result.text() == "город"


@allure.epic("Translators")
@allure.feature("Google")
def test_google_joins_sentence_segments():
    answer = [
        [
            ["Привет, мир. ", "Hello world. ", None, None, 10],
            ["Как дела?", "How are you?", None, None, 10],
        ],
        None,
        "en",
    ]

    assert parse_google_answer(answer, "Hello world. How are you?") == GoogleTranslation(
        "Привет, мир. Как дела?"
    )


@allure.epic("Translators")
@allure.feature("Google")
def test_google_part_of_speech_label_may_be_missing():
    answer = [[["tot", "dead", None, None, 10]], [["", ["tot", "gestorben"], [], "dead", 0]]]

    assert parse_google_answer(answer, "dead").text() == "tot\ntot, gestorben"


@allure.epic("Translators")
@allure.feature("Google")
def test_google_echo_with_alternatives_is_a_translation():
    answer = [[["Hotel", "Hotel", None, None, 10]], [["noun", ["Hotel"], [], "Hotel", 1]]]

    assert parse_google_answer(answer, "Hotel").translation == "Hotel"


@allure.epic("Translators")
@allure.feature("Google")
@pytest.mark.parametrize(
    "answer",
    [
        pytest.param([[["xqzv", "xqzv", None, None, 3]], None, "en"], id="echo"),
        pytest.param([[["", "", None, None, 5]], None, "en"], id="empty"),
        pytest.param([[["  ", " ", None, None, 5]], None, "en"], id="blank"),
        pytest.param([None, None, "en"], id="no-segments"),
        pytest.param({"error": "unexpected"}, id="not-a-list"),
    ],
)
def test_google_no_translation(answer):
    endpoint = GoogleEndpoint(answer)

    with pytest.raises(TranslatorError) as error:
        _translator(endpoint).lookup("xqzv")

    assert error.value.kind == TranslatorError.NOT_FOUND
    assert endpoint.clients == ["dict-chrome-ex"]


@allure.epic("Translators")
@allure.feature("Google")
def test_google_selection_too_long_for_the_endpoint_is_not_sent():
    endpoint = GoogleEndpoint(SPRING)

    with pytest.raises(TranslatorError) as error:
        _translator(endpoint).lookup("Привет мир. " * 400)

    assert error.value.kind == TranslatorError.TOO_LONG
    assert endpoint.requests == []


@allure.epic("Translators")
@allure.feature("Google")
@pytest.mark.parametrize(
    "language, code",
    [("english", "en"), ("serbian", "sr"), ("German", "de"), ("ru", "ru"), ("zh-CN", "zh-CN")],
)
def test_google_language_names_become_codes(language, code):
    assert google_code(language) == code


@allure.epic("Translators")
@allure.feature("Google")
def test_google_unknown_language_is_unsupported():
    with pytest.raises(TranslatorError) as error:
        GoogleTranslator("klingon", "russian")

    assert error.value.kind == TranslatorError.UNSUPPORTED


@allure.epic("Translators")
@allure.feature("Google")
def test_google_translator_option_uses_the_json_endpoint():
    translator = Translator("Google", "english", "russian")

    assert isinstance(translator._translator, GoogleTranslator)
    assert (translator._translator.source, translator._translator.target) == ("en", "ru")


@allure.epic("Translators")
@allure.feature("Google")
def test_google_failure_is_not_cached():
    translator = Translator("Google", "english", "russian")
    endpoint = GoogleEndpoint(httpx.ConnectError("down"), SPRING)
    translator._translator = _translator(endpoint)

    with pytest.raises(TranslatorError):
        translator.translate(Term("spring"))
    assert translator.translate(Term("spring", "a ⟦spring⟧ creaked")).startswith("весна\n")
    assert translator.translate(Term("spring", "early ⟦spring⟧")).startswith("весна\n")
    assert len(endpoint.requests) == 2


def _dictionary_popup(client, user, book, endpoint):
    client.force_login(user)
    language_preferences = LanguagePreferences.get_or_create_language_preferences(
        user=user, language=book.language
    )
    language_preferences.inline_translation_parameters = {"dictionary": "Google"}
    language_preferences.save()
    with patch(
        "lexiflux.views.lexical_views.get_translator",
        return_value=_translator(endpoint),
    ):
        return client.get(
            reverse("translate"),
            {
                "lexical-article": "0",
                "book-code": book.code,
                "book-page-number": "1",
                "word-ids": "2",
            },
        )


@allure.epic("Translators")
@allure.feature("Google")
@pytest.mark.django_db
def test_google_popup_shows_alternatives_and_remembers_the_translation(client, user, book):
    response = _dictionary_popup(client, user, book, GoogleEndpoint(SPRING))

    assert response.status_code == 200
    assert response.json() == {
        "article": "весна\n"
        "*noun:* весна, пружина, рессора, источник, родник, ключ, упругость, прыжок\n"
        "*verb:* возникать, пружинить",
    }
    assert TranslationHistory.objects.get(user=user).translation == "весна"


@allure.epic("Translators")
@allure.feature("Google")
@pytest.mark.django_db
@pytest.mark.parametrize(
    "answers, message",
    [
        pytest.param(
            [httpx.Response(429, text=SORRY_PAGE)] * 3,
            "Google is refusing requests right now (rate limit)",
            id="rate-limit",
        ),
        pytest.param(
            [httpx.ConnectTimeout("slow")],
            "Could not reach Google.",
            id="network",
        ),
        pytest.param(
            [[[["page", "page", None, None, 3]], None, "en"]],
            "Google found no translation.",
            id="not-found",
        ),
    ],
)
def test_google_popup_failure_is_an_alert(answers, message, client, user, book):
    response = _dictionary_popup(client, user, book, GoogleEndpoint(*answers))

    assert response.status_code == 200
    data = response.json()
    assert data["error"] is True
    assert 'class="alert' in data["article"]
    assert message in data["article"]
    assert not TranslationHistory.objects.filter(user=user).exists()


@allure.epic("Translators")
@allure.feature("Google")
@pytest.mark.django_db
def test_google_sidebar_article_shows_alternatives_as_lines(client, user, book):
    client.force_login(user)
    language_preferences = LanguagePreferences.get_or_create_language_preferences(
        user=user, language=book.language
    )
    LexicalArticle.objects.create(
        language_preferences=language_preferences,
        type="Dictionary",
        title="Google",
        parameters={"dictionary": "Google"},
        order=10,
    )
    answer = [[["<страница>", "page", None, None, 10]], [["noun", ["страница"], [], "page", 1]]]

    with patch(
        "lexiflux.views.lexical_views.get_translator",
        return_value=_translator(GoogleEndpoint(answer)),
    ):
        response = client.get(
            reverse("translate_stream"),
            {
                "lexical-article": "5",
                "book-code": book.code,
                "book-page-number": "1",
                "word-ids": "2",
            },
        )
        body = b"".join(response.streaming_content)
    events = [json.loads(line) for line in body.splitlines()]

    assert events == [
        {"event": "delta", "text": "&lt;страница&gt;<br>*noun:* страница"},
        {"event": "done"},
    ]
