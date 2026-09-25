import allure
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from unittest.mock import patch, MagicMock

from lexiflux.language.translation import (
    AVAILABLE_TRANSLATORS,
    Term,
    Translator,
    TranslatorError,
    get_translator,
)
from lexiflux.language_preferences_default import LINGEA_ARTICLE
from lexiflux.models import LanguagePreferences
from tests.conftest import USER_PASSWORD


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
@patch("lexiflux.views.lexical_views.get_translator")
def test_translate_view_success(mock_get_translator, client, user, book):
    client.force_login(user)
    language_preferences = LanguagePreferences.get_or_create_language_preferences(
        user=user, language=book.language
    )

    mock_translator = mock_get_translator.return_value
    mock_translator.translate.return_value = "Hola"

    book_code = "some-book-code"
    response = client.get(
        reverse("translate"),
        {
            "lexical-article": "0",
            "text": "Hello",
            "book-code": book_code,
            "book-page-number": "1",
            "word-ids": "1.2.3",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"article": "Hola"}
    mock_get_translator.assert_called_once_with(
        "LLMTranslation",
        book.language.name,
        language_preferences.user_language.name,
    )
    (term,) = mock_translator.translate.call_args.args
    assert term == Term("of page 1", "Content ⟦of page 1⟧")
    assert term.user == user


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@patch("lexiflux.language.translation.Translator")
def test_get_translator(mock_translator, book, user):
    language_preferences = LanguagePreferences.get_or_create_language_preferences(
        user=user, language=book.language
    )

    result = get_translator(
        "Google",
        book.language.name.lower(),
        language_preferences.user_language.name.lower(),
    )
    mock_translator.assert_called_once_with(
        "Google",
        book.language.name.lower(),
        language_preferences.user_language.name.lower(),
    )
    assert isinstance(result, mock_translator.return_value.__class__)


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_translate_view_approved_users_only(client, user, book):
    # force_login() skip auth backed, so we do full login here
    client.login(username=user.username, password=USER_PASSWORD)  # user.password is hashed

    book_code = "some-book-code"
    response = client.get(
        reverse("translate"),
        {
            "lexical-article": "0",
            "text": "Hello",
            "book-code": book_code,
            "book-page-number": "1",
            "word-ids": "1.2.3",
        },
    )
    assert response.status_code == 302
    assert "login/?next=" in response.url


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_translator_translate(book, user):
    mock_translation = "This is a test translation."

    with patch.dict(AVAILABLE_TRANSLATORS, {"Google": (MagicMock(), "Google")}) as mock_translators:
        mock_google_translator = mock_translators["Google"][0].return_value
        mock_google_translator.translate.return_value = mock_translation

        language_preferences = LanguagePreferences.get_or_create_language_preferences(
            user=user, language=book.language
        )
        translator = Translator(
            "Google",
            book.language.google_code,
            language_preferences.user_language.google_code,
        )
        result = translator.translate(Term("This is a test."))

        assert result == mock_translation
        mock_google_translator.translate.assert_called_once_with(Term("This is a test."))


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_translate_view_retired_model_error(client, user, book):
    """Test that retired model error shows friendly HTML error message"""

    client.force_login(user)
    language_preferences = LanguagePreferences.get_or_create_language_preferences(
        user=user, language=book.language
    )
    # Set to an AI model type that would use LLM
    language_preferences.inline_translation_type = "Translate"
    language_preferences.inline_translation_parameters = {
        "model": "claude-sonnet-4-0"  # not an offered model
    }
    language_preferences.save()

    response = client.get(
        reverse("translate"),
        {
            "lexical-article": "0",
            "book-code": book.code,
            "book-page-number": "1",
            "word-ids": "1.2",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["error"] is True
    assert "AI Model No Longer Available" in data["article"]
    assert "claude-sonnet-4-0" in data["article"]
    assert "/language-preferences/" in data["article"]


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_translate_keeps_the_whole_error_alert_despite_its_hr(client, user, book):
    client.force_login(user)
    language_preferences = LanguagePreferences.get_or_create_language_preferences(
        user=user, language=book.language
    )
    language_preferences.inline_translation_type = "Translate"
    language_preferences.inline_translation_parameters = {"model": "claude-sonnet-4-0"}
    language_preferences.save()

    response = client.get(
        reverse("translate"),
        {
            "lexical-article": "0",
            "book-code": book.code,
            "book-page-number": "1",
            "word-ids": "1.2",
        },
    )

    article = response.json()["article"]
    assert "<hr>" in article
    assert "Update Language Preferences" in article
    assert article.count("<div") == article.count("</div>")


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
@patch("lexiflux.views.lexical_views.generate_article", return_value="AI answer<hr>more")
def test_translate_inline_ai_goes_through_generate_article(mock_generate, client, user, book):
    client.force_login(user)
    language_preferences = LanguagePreferences.get_or_create_language_preferences(
        user=user, language=book.language
    )
    language_preferences.inline_translation_type = "Translate"
    language_preferences.inline_translation_parameters = {"model": "gpt", "effort": "low"}
    language_preferences.save()

    response = client.get(
        reverse("translate"),
        {
            "lexical-article": "0",
            "book-code": book.code,
            "book-page-number": "1",
            "word-ids": "2",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"article": "AI answer"}
    req = mock_generate.call_args.args[0]
    assert req.article_type == "Translate"
    assert (req.model, req.effort, req.tier) == ("gpt", "low", None)
    assert req.word == "page"
    assert req.sentence == "Content of page 1"
    assert req.text_language == book.language.name
    assert req.user_language == language_preferences.user_language.name
    assert req.user == user


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_translate_serves_only_the_inline_article(client, user, book):
    client.force_login(user)

    response = client.get(
        reverse("translate"),
        {
            "lexical-article": "1",
            "book-code": book.code,
            "book-page-number": "1",
            "word-ids": "2",
        },
    )

    assert response.status_code == 400


def _reader(reader, book, user):
    if reader == "owner":
        return user
    book.public = reader == "other-public"
    book.save()
    return get_user_model().objects.create_user(
        username="reader", email="reader@example.com", password=USER_PASSWORD, is_approved=True
    )


READERS = [("owner", 200), ("other-private", 403), ("other-public", 200)]


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
@pytest.mark.parametrize("reader, status", READERS)
@patch("lexiflux.views.lexical_views.get_translator")
def test_translate_checks_the_book_can_be_read(
    mock_get_translator, reader, status, client, user, book
):
    mock_get_translator.return_value.translate.side_effect = lambda term: f"ECHO:{term.word}"
    client.force_login(_reader(reader, book, user))

    response = client.get(
        reverse("translate"),
        {
            "lexical-article": "0",
            "book-code": book.code,
            "book-page-number": "1",
            "word-ids": "0.1.2.3",
        },
    )

    assert response.status_code == status
    if status == 403:
        assert "ECHO" not in response.content.decode()
        mock_get_translator.return_value.translate.assert_not_called()
    else:
        assert response.json() == {"article": "ECHO:Content of page 1"}


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
@pytest.mark.parametrize("reader, status", READERS)
@patch("lexiflux.views.lexical_views.get_translator")
def test_translate_stream_checks_the_book_can_be_read(
    mock_get_translator, reader, status, client, user, book
):
    from lexiflux.models import LexicalArticle

    mock_get_translator.return_value.translate.side_effect = lambda term: f"ECHO:{term.word}"
    reading_user = _reader(reader, book, user)
    client.force_login(reading_user)
    language_preferences = LanguagePreferences.get_or_create_language_preferences(
        user=reading_user, language=book.language
    )
    LexicalArticle.objects.create(
        language_preferences=language_preferences,
        type="Dictionary",
        title="Google",
        parameters={"dictionary": "Google"},
        order=10,
    )
    article_number = language_preferences.get_lexical_articles().count()

    response = client.get(
        reverse("translate_stream"), _stream_params(book, article_number, word_ids="0.1.2.3")
    )

    assert response.status_code == status
    if status == 403:
        assert not response.streaming
        mock_get_translator.return_value.translate.assert_not_called()
    else:
        assert _stream_events(response) == [
            {"event": "delta", "text": "ECHO:Content of page 1"},
            {"event": "done"},
        ]


def _stream_params(book, lexical_article, word_ids="2"):
    return {
        "lexical-article": str(lexical_article),
        "book-code": book.code,
        "book-page-number": "1",
        "word-ids": word_ids,
    }


def _stream_events(response):
    import json

    body = b"".join(response.streaming_content).decode("utf-8")
    assert body.endswith("\n")
    return [json.loads(line) for line in body.splitlines()]


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_translate_stream_ai_article_events(client, user, book):
    from lexiflux.language.llm import ArticleError, ArticleEvent

    client.force_login(user)
    language_preferences = LanguagePreferences.get_or_create_language_preferences(
        user=user, language=book.language
    )
    requests = []

    def fake_stream(req):
        requests.append(req)
        yield ArticleEvent.delta("Hel")
        yield ArticleEvent.delta("lo")
        yield ArticleEvent.replace("Whole answer")
        yield ArticleEvent.error(ArticleError("cut_off", "<div>cut off</div>"))

    with patch("lexiflux.views.lexical_views.stream_article", side_effect=fake_stream):
        response = client.get(reverse("translate_stream"), _stream_params(book, 2))
        events = _stream_events(response)

    assert response.status_code == 200
    assert response.streaming
    assert response["Content-Type"] == "application/x-ndjson"
    assert response["Cache-Control"] == "no-cache"
    assert response["X-Accel-Buffering"] == "no"
    assert events == [
        {"event": "delta", "text": "Hel"},
        {"event": "delta", "text": "lo"},
        {"event": "replace", "text": "Whole answer"},
        {"event": "error", "kind": "cut_off", "html": "<div>cut off</div>"},
        {"event": "done"},
    ]
    (req,) = requests
    assert req.article_type == "In depth"
    assert (req.model, req.effort, req.tier) == ("gpt", "none", "priority")
    assert req.word == "page"
    assert req.sentence == "Content of page 1"
    assert req.text_language == book.language.name
    assert req.user_language == language_preferences.user_language.name
    assert req.user == user


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_translate_stream_ai_article_over_fake_broker(client, user, book):
    client.force_login(user)
    LanguagePreferences.get_or_create_language_preferences(user=user, language=book.language)
    stream = MagicMock()
    stream.__enter__.return_value = iter(["An ", "article"])
    llms = MagicMock()
    llms.stream.return_value = stream

    with patch("lexiflux.language.llm.llms_for", return_value=llms):
        response = client.get(reverse("translate_stream"), _stream_params(book, 1))
        events = _stream_events(response)

    assert events == [
        {"event": "delta", "text": "An "},
        {"event": "delta", "text": "article"},
        {"event": "done"},
    ]
    assert llms.stream.call_args.kwargs["operation"] == "AI dictionary"


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_translate_stream_site_article_events(client, user, book):
    client.force_login(user)
    language_preferences = LanguagePreferences.get_or_create_language_preferences(
        user=user, language=book.language
    )

    response = client.get(reverse("translate_stream"), _stream_params(book, 4))

    assert response.status_code == 200
    assert _stream_events(response) == [
        {
            "event": "site",
            "url": f"https://glosbe.com/{book.language.google_code}/"
            f"{language_preferences.user_language.google_code}/page",
            "window": True,
        },
        {"event": "done"},
    ]


def _lingea_stream(client, user, book, user_language, content="Љубав и кућа", word_ids="0"):
    from lexiflux.models import Language

    serbian = Language.objects.get(google_code="sr")
    book.language = serbian
    book.save()
    page = book.pages.get(number=1)
    page.content = content
    page.save()
    client.force_login(user)
    language_preferences = LanguagePreferences.get_or_create_language_preferences(
        user=user, language=serbian
    )
    language_preferences.user_language = Language.objects.get(google_code=user_language)
    language_preferences.save()
    language_preferences.lexical_articles.create(
        type="Site", title="lingea", parameters=dict(LINGEA_ARTICLE["parameters"]), order=10
    )
    titles = [article.title for article in language_preferences.get_lexical_articles()]
    return _stream_events(
        client.get(
            reverse("translate_stream"),
            _stream_params(book, titles.index("lingea") + 1, word_ids=word_ids),
        )
    )


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
@pytest.mark.parametrize(
    "content, word_ids, term",
    [
        ("Љубав и кућа", "0", "Ljubav"),
        ("Љубав и кућа", "2", "ku%C4%87a"),
        ("Ljubav i kuća", "2", "ku%C4%87a"),
    ],
)
def test_translate_stream_lingea_link_has_the_term_in_latin(
    client, user, book, content, word_ids, term
):
    assert _lingea_stream(client, user, book, "ru", content, word_ids) == [
        {
            "event": "site",
            "url": f"https://recnici.lingea.rs/rusko-srpski/{term}",
            "window": True,
        },
        {"event": "done"},
    ]


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
@pytest.mark.parametrize(
    "user_language, dictionary",
    [("ru", "rusko-srpski"), ("en", "englesko-srpski"), ("de", "nemacko-srpski")],
)
def test_translate_stream_lingea_link_names_the_user_language(
    client, user, book, user_language, dictionary
):
    assert _lingea_stream(client, user, book, user_language)[0]["url"] == (
        f"https://recnici.lingea.rs/{dictionary}/Ljubav"
    )


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_translate_stream_lingea_without_the_user_language_is_an_alert(client, user, book):
    events = _lingea_stream(client, user, book, "ka")

    assert [event["event"] for event in events] == ["error", "done"]
    assert "Lingea has no Georgian–Serbian dictionary" in events[0]["html"]


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
@patch("lexiflux.views.lexical_views.get_translator")
def test_translate_stream_dictionary_article_events(mock_get_translator, client, user, book):
    from lexiflux.models import LexicalArticle

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
    mock_get_translator.return_value.translate.return_value = "stranica"

    response = client.get(reverse("translate_stream"), _stream_params(book, 5))

    assert _stream_events(response) == [
        {"event": "delta", "text": "stranica"},
        {"event": "done"},
    ]
    (term,) = mock_get_translator.return_value.translate.call_args.args
    assert term == Term("page", "Content of ⟦page⟧ 1")


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
@patch("lexiflux.views.lexical_views.get_translator")
def test_translate_stream_dictionary_failure_is_an_error_event(
    mock_get_translator, client, user, book
):
    from lexiflux.models import LexicalArticle

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
    mock_get_translator.return_value.translate.side_effect = RuntimeError("down <now>")

    events = _stream_events(client.get(reverse("translate_stream"), _stream_params(book, 5)))

    assert [e["event"] for e in events] == ["error", "done"]
    assert events[0]["kind"] == "generic"
    assert "RuntimeError" in events[0]["html"]
    assert "down" not in events[0]["html"]


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_translate_stream_is_not_gzipped(client, user, book):
    from lexiflux.language.llm import ArticleEvent

    client.force_login(user)
    LanguagePreferences.get_or_create_language_preferences(user=user, language=book.language)

    def long_stream(req):
        for _ in range(20):
            yield ArticleEvent.delta("a long enough answer to be worth compressing " * 5)

    with patch("lexiflux.views.lexical_views.stream_article", side_effect=long_stream):
        response = client.get(
            reverse("translate_stream"),
            _stream_params(book, 1),
            HTTP_ACCEPT_ENCODING="gzip, deflate",
        )
        events = _stream_events(response)

    assert not response.has_header("Content-Encoding")
    assert len(events) == 21
    assert events[-1] == {"event": "done"}


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_other_responses_are_still_gzipped(client, user, book):
    client.force_login(user)

    response = client.get(reverse("language-preferences"), HTTP_ACCEPT_ENCODING="gzip")

    assert response["Content-Encoding"] == "gzip"


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_translate_stream_closing_the_response_closes_the_article_stream(client, user, book):
    from lexiflux.language.llm import ArticleEvent

    client.force_login(user)
    LanguagePreferences.get_or_create_language_preferences(user=user, language=book.language)
    closed = []

    def endless_stream(req):
        try:
            while True:
                yield ArticleEvent.delta("x")
        finally:
            closed.append(True)

    with patch("lexiflux.views.lexical_views.stream_article", side_effect=endless_stream):
        response = client.get(reverse("translate_stream"), _stream_params(book, 1))
        next(iter(response.streaming_content))
        response.close()

    assert closed == [True]


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_translate_stream_unknown_article(client, user, book):
    client.force_login(user)
    LanguagePreferences.get_or_create_language_preferences(user=user, language=book.language)

    response = client.get(reverse("translate_stream"), _stream_params(book, 99))

    assert response.status_code == 404
    assert response.json() == {"error": "Lexical article not found"}


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_translate_stream_requires_login(client, book):
    response = client.get(reverse("translate_stream"), _stream_params(book, 1))

    assert response.status_code == 302
    assert "login/?next=" in response.url


def _inline_ai(client, user, book):
    client.force_login(user)
    language_preferences = LanguagePreferences.get_or_create_language_preferences(
        user=user, language=book.language
    )
    language_preferences.inline_translation_type = "Translate"
    language_preferences.inline_translation_parameters = {"model": "gpt", "effort": "low"}
    language_preferences.save()


def _get_inline(client, book):
    return client.get(
        reverse("translate"),
        {
            "lexical-article": "0",
            "book-code": book.code,
            "book-page-number": "1",
            "word-ids": "2",
        },
    )


def _no_keys_error():
    from lexiflux.language.llm import ArticleError

    return ArticleError("no_keys", "<div>Set GROQ_API_KEY</div>")


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_translate_ai_error_saves_no_history(client, user, book):
    from lexiflux.models import TranslationHistory

    _inline_ai(client, user, book)

    with patch("lexiflux.views.lexical_views.generate_article", side_effect=_no_keys_error()):
        response = _get_inline(client, book)

    assert response.json() == {"article": "<div>Set GROQ_API_KEY</div>", "error": True}
    assert not TranslationHistory.objects.filter(user=user).exists()


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_translate_ai_error_keeps_the_earlier_translation(client, user, book):
    from lexiflux.models import TranslationHistory

    _inline_ai(client, user, book)
    with patch("lexiflux.views.lexical_views.generate_article", return_value="страница"):
        _get_inline(client, book)
    before = TranslationHistory.objects.get(user=user, term="page")

    with patch("lexiflux.views.lexical_views.generate_article", side_effect=_no_keys_error()):
        response = _get_inline(client, book)

    assert response.json()["error"] is True
    after = TranslationHistory.objects.get(user=user, term="page")
    assert after.translation == "страница"
    assert after.lookup_count == 1
    assert after.last_lookup == before.last_lookup


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_translate_success_creates_then_updates_history(client, user, book):
    from lexiflux.models import TranslationHistory

    _inline_ai(client, user, book)
    with patch("lexiflux.views.lexical_views.generate_article", return_value="страница<hr>more"):
        _get_inline(client, book)
    first = TranslationHistory.objects.get(user=user, term="page")
    assert (first.translation, first.lookup_count) == ("страница", 1)

    with patch("lexiflux.views.lexical_views.generate_article", return_value="лист"):
        _get_inline(client, book)

    second = TranslationHistory.objects.get(user=user, term="page")
    assert (second.translation, second.lookup_count) == ("лист", 2)
    assert second.book == book


TRANSLATOR_FAILURES = [
    pytest.param(
        "RateLimit",
        "Google is refusing requests right now (rate limit)",
        id="rate-limit",
    ),
    pytest.param("Network", "Could not reach Google.", id="network"),
    pytest.param("NotFound", "Google found no translation.", id="not-found"),
    pytest.param(
        "Unsupported",
        "Google does not support this language pair. Pick another translator",
        id="unsupported-language",
    ),
    pytest.param("TooLong", "Google cannot translate a selection this long.", id="too-long"),
    pytest.param("EmptyResult", "Google found no translation.", id="empty-result"),
    pytest.param("NoneResult", "Google found no translation.", id="none-result"),
    pytest.param("KeyError", "Google failed (KeyError)", id="other"),
]
RAW_EXCEPTION_TEXT = "raw-secret-detail <b>"
PERMANENT_FAILURES = {"Unsupported", "TooLong"}


def _translator_failure(name):
    return {
        "RateLimit": TranslatorError(TranslatorError.RATE_LIMIT, RAW_EXCEPTION_TEXT),
        "Network": TranslatorError(TranslatorError.NETWORK, RAW_EXCEPTION_TEXT),
        "NotFound": TranslatorError(TranslatorError.NOT_FOUND, RAW_EXCEPTION_TEXT),
        "Unsupported": TranslatorError(TranslatorError.UNSUPPORTED, RAW_EXCEPTION_TEXT),
        "TooLong": TranslatorError(TranslatorError.TOO_LONG, RAW_EXCEPTION_TEXT),
        "EmptyResult": ["  "],
        "NoneResult": [None],
        "KeyError": KeyError(RAW_EXCEPTION_TEXT),
    }[name]


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
@pytest.mark.parametrize("failure, message", TRANSLATOR_FAILURES)
@patch("lexiflux.views.lexical_views.get_translator")
def test_translate_inline_translator_failure_is_an_alert(
    mock_get_translator, failure, message, client, user, book, caplog
):
    from lexiflux.models import TranslationHistory

    client.force_login(user)
    language_preferences = LanguagePreferences.get_or_create_language_preferences(
        user=user, language=book.language
    )
    language_preferences.inline_translation_parameters = {"dictionary": "Google"}
    language_preferences.save()
    mock_get_translator.return_value.translate.side_effect = _translator_failure(failure)

    response = client.get(
        reverse("translate"),
        {
            "lexical-article": "0",
            "book-code": book.code,
            "book-page-number": "1",
            "word-ids": "2",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["error"] is True
    assert 'class="alert' in data["article"]
    assert message in data["article"]
    assert "raw-secret-detail" not in data["article"]
    assert "<b>" not in data["article"]
    if failure in PERMANENT_FAILURES:
        assert "later" not in data["article"]
    assert not TranslationHistory.objects.filter(user=user).exists()
    assert "Dictionary article failed" in caplog.text
    assert ("Traceback" in caplog.text) == (failure == "KeyError")


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
@pytest.mark.parametrize("failure, message", TRANSLATOR_FAILURES)
@patch("lexiflux.views.lexical_views.get_translator")
def test_translate_stream_translator_failure_is_an_alert(
    mock_get_translator, failure, message, client, user, book
):
    from lexiflux.models import LexicalArticle, TranslationHistory

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
    mock_get_translator.return_value.translate.side_effect = _translator_failure(failure)

    response = client.get(reverse("translate_stream"), _stream_params(book, 5))
    events = _stream_events(response)

    assert response.status_code == 200
    assert [e["event"] for e in events] == ["error", "done"]
    assert 'class="alert' in events[0]["html"]
    assert message in events[0]["html"]
    assert "raw-secret-detail" not in events[0]["html"]
    if failure in PERMANENT_FAILURES:
        assert "later" not in events[0]["html"]
    assert not TranslationHistory.objects.filter(user=user).exists()
