import logging
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import allure
import pytest
from django.test import override_settings
from django.urls import reverse
from llmbroker import LLMTimeoutError, NoLLMAvailableError, RateLimitError

from lexiflux.language import llm, wiktionary
from lexiflux.language.translation import GoogleTranslator
from lexiflux.models import Language, LanguagePreferences, TranslationHistory
from lexiflux.views import lexical_views
from tests.kaikki import Kaikki

SOFA = "The old sofa had broken springs."
SEASON = "Early springs came."


class FakePool:
    def __init__(self, *answers):
        self.answers = list(answers)
        self.prompts = []

    def ask(self, prompt, **kwargs):
        self.prompts.append(prompt)
        answer = self.answers.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        return SimpleNamespace(text=answer)


@pytest.fixture
def pool():
    holder = {"pool": FakePool()}
    with patch("lexiflux.language.llm.llms_for", side_effect=lambda user: holder["pool"]):
        yield holder


@pytest.fixture
def kaikki(db):
    fake = Kaikki()
    with patch.object(wiktionary, "http_client", fake.client):
        yield fake


@pytest.fixture
def held():
    """The background work of each lookup, held until the test runs it."""
    work = []
    with patch.object(lexical_views, "in_background", side_effect=work.append):
        yield work


def _preferences(user, book, translator, user_language="Russian"):
    preferences = LanguagePreferences.get_or_create_language_preferences(
        user=user, language=book.language
    )
    preferences.user_language = Language.objects.get(name=user_language)
    preferences.inline_translation_type = "Dictionary"
    preferences.inline_translation_parameters = {"dictionary": translator}
    preferences.save()


def _get(client, book, word_id):
    return client.get(
        reverse("translate"),
        {
            "lexical-article": "0",
            "book-code": book.code,
            "book-page-number": "1",
            "word-ids": word_id,
        },
    )


def _lookup(client, user, book, text, translator="Wiktionary", word_id="5"):
    page = book.pages.get(number=1)
    page.content, page.word_slices, page.word_to_sentence_map = text, None, None
    page.save()
    client.force_login(user)
    _preferences(user, book, translator)
    return _get(client, book, word_id)


def _entry(user):
    entry = TranslationHistory.objects.get(user=user)
    return entry.translation, entry.translation_from_llm


@allure.epic("Vocabulary")
@allure.feature("History translation")
@pytest.mark.django_db
def test_wiktionary_popup_shows_its_senses_and_the_history_takes_the_llm_sense(
    pool, kaikki, client, user, book
):
    pool["pool"] = FakePool("пружина")

    data = _lookup(client, user, book, SOFA).json()

    assert data["html"] is True
    assert "<li>весна</li>" in data["article"]
    assert _entry(user) == ("пружина", True)
    assert pool["pool"].prompts[0].endswith("Text: The old sofa had broken ⟦springs⟧.")


@allure.epic("Vocabulary")
@allure.feature("History translation")
@pytest.mark.django_db
def test_google_popup_history_takes_the_llm_sense(pool, client, user, book):
    pool["pool"] = FakePool("пружина")

    with patch.object(GoogleTranslator, "translate", return_value="весна\n*noun:* весна"):
        data = _lookup(client, user, book, SOFA, translator="Google").json()

    assert data == {"article": "весна\n*noun:* весна"}
    assert _entry(user) == ("пружина", True)


@allure.epic("Vocabulary")
@allure.feature("History translation")
@pytest.mark.django_db
def test_the_popup_answers_before_the_llm_is_asked(pool, kaikki, held, client, user, book):
    pool["pool"] = FakePool("пружина")

    data = _lookup(client, user, book, SOFA).json()

    assert "<li>весна</li>" in data["article"]
    assert pool["pool"].prompts == []
    assert _entry(user) == ("весна", False)
    (work,) = held
    work()
    assert _entry(user) == ("пружина", True)


@allure.epic("Vocabulary")
@allure.feature("History translation")
@pytest.mark.django_db
def test_an_llm_translation_stays_until_the_new_one_arrives(pool, kaikki, held, client, user, book):
    pool["pool"] = FakePool("пружина", "весна")
    _lookup(client, user, book, SOFA)
    held.pop()()

    _lookup(client, user, book, SEASON, word_id="1")

    assert _entry(user) == ("пружина", True)
    held.pop()()
    assert _entry(user) == ("весна", True)
    assert TranslationHistory.objects.get(user=user).lookup_count == 2


@allure.epic("Vocabulary")
@allure.feature("History translation")
@pytest.mark.django_db
def test_a_late_answer_for_an_earlier_lookup_does_not_replace_a_later_one(
    pool, kaikki, held, client, user, book
):
    pool["pool"] = FakePool("пружина", "весна")
    _lookup(client, user, book, SEASON, word_id="1")
    _lookup(client, user, book, SOFA)
    earlier, later = held

    later()
    earlier()

    assert _entry(user) == ("пружина", True)


@allure.epic("Vocabulary")
@allure.feature("History translation")
@pytest.mark.django_db
@pytest.mark.parametrize(
    "failure",
    [
        LLMTimeoutError("slow"),
        NoLLMAvailableError("none", reason="no_keys"),
        ProcessLookupError("unexpected"),
    ],
    ids=["timeout", "no keys", "other"],
)
def test_a_failed_llm_translation_changes_nothing_and_is_retried(
    pool, kaikki, failure, client, user, book
):
    pool["pool"] = FakePool(failure, "пружина")

    _lookup(client, user, book, SOFA)

    assert _entry(user) == ("весна", False)

    _lookup(client, user, book, SOFA)

    assert _entry(user) == ("пружина", True)
    assert len(pool["pool"].prompts) == 2


@allure.epic("Vocabulary")
@allure.feature("History translation")
@pytest.mark.django_db
@pytest.mark.parametrize(
    "failure",
    [
        LLMTimeoutError("slow"),
        NoLLMAvailableError("none", reason="no_keys"),
        NoLLMAvailableError("busy", reason="timeout"),
        RateLimitError("slow down", status=429, retry_after=12),
    ],
    ids=["timeout", "no keys", "busy", "rate limit"],
)
def test_a_known_llm_failure_logs_one_line_about_the_history_translation(
    pool, kaikki, failure, caplog, client, user, book
):
    pool["pool"] = FakePool(failure)

    _lookup(client, user, book, SOFA)

    (record,) = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert record.getMessage() == f"History translation of 'springs' failed: {failure!r}"
    assert record.exc_info is None
    assert "AI article" not in caplog.text


@allure.epic("Vocabulary")
@allure.feature("History translation")
@pytest.mark.django_db
def test_an_unexpected_llm_failure_logs_the_history_translation_with_its_traceback(
    pool, kaikki, caplog, client, user, book
):
    pool["pool"] = FakePool(ProcessLookupError("unexpected"))

    _lookup(client, user, book, SOFA)

    (record,) = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert record.getMessage() == "History translation of 'springs' failed"
    assert record.exc_info[0] is ProcessLookupError
    assert "AI article" not in caplog.text


@allure.epic("Vocabulary")
@allure.feature("History translation")
@pytest.mark.django_db
def test_a_failed_llm_translation_keeps_the_earlier_one(pool, kaikki, client, user, book):
    pool["pool"] = FakePool("пружина", LLMTimeoutError("slow"))
    _lookup(client, user, book, SOFA)

    _lookup(client, user, book, SEASON, word_id="1")

    assert _entry(user) == ("пружина", True)


@allure.epic("Vocabulary")
@allure.feature("History translation")
@pytest.mark.django_db
def test_a_kept_llm_translation_keeps_its_passage_and_the_new_passage_is_asked_again(
    pool, kaikki, client, user, book
):
    pool["pool"] = FakePool("пружина", LLMTimeoutError("slow"), "весна")
    _lookup(client, user, book, SOFA)

    _lookup(client, user, book, SEASON, word_id="1")

    entry = TranslationHistory.objects.get(user=user)
    assert (entry.translation, entry.translation_from_llm) == ("пружина", True)
    assert "sofa" in entry.context

    _lookup(client, user, book, SEASON, word_id="1")

    entry = TranslationHistory.objects.get(user=user)
    assert (entry.translation, entry.translation_from_llm) == ("весна", True)
    assert "Early" in entry.context
    assert len(pool["pool"].prompts) == 3


@allure.epic("Vocabulary")
@allure.feature("History translation")
@pytest.mark.django_db
def test_a_passage_with_its_llm_translation_is_not_asked_again_after_a_restart(
    pool, kaikki, held, client, user, book
):
    pool["pool"] = FakePool("пружина")
    _lookup(client, user, book, SOFA)
    held.pop()()
    llm.clear_cache()

    _lookup(client, user, book, SOFA)

    assert held == []
    assert _entry(user) == ("пружина", True)
    assert TranslationHistory.objects.get(user=user).lookup_count == 2


@allure.epic("Vocabulary")
@allure.feature("History translation")
@pytest.mark.django_db
def test_an_empty_llm_answer_changes_nothing(pool, kaikki, client, user, book):
    pool["pool"] = FakePool("  ")

    _lookup(client, user, book, SOFA)

    assert _entry(user) == ("весна", False)


@allure.epic("Vocabulary")
@allure.feature("History translation")
@pytest.mark.django_db
def test_an_llm_translation_into_another_language_is_replaced(
    pool, kaikki, held, client, user, book
):
    pool["pool"] = FakePool("пружина")
    _lookup(client, user, book, SOFA)
    held.pop()()
    _preferences(user, book, "Google", user_language="German")

    with patch.object(GoogleTranslator, "translate", return_value="Frühling"):
        _get(client, book, "5")

    assert _entry(user) == ("Frühling", False)
    assert len(held) == 1


@allure.epic("Vocabulary")
@allure.feature("History translation")
@pytest.mark.django_db
def test_llm_translation_popup_saves_its_own_answer_as_llm(pool, held, client, user, book):
    pool["pool"] = FakePool("пружина", "весна")

    assert _lookup(client, user, book, SOFA, translator="LLMTranslation").json() == {
        "article": "пружина"
    }
    assert _entry(user) == ("пружина", True)

    _lookup(client, user, book, SEASON, translator="LLMTranslation", word_id="1")

    assert _entry(user) == ("весна", True)
    assert held == []


@allure.epic("Vocabulary")
@allure.feature("History translation")
@pytest.mark.django_db
def test_an_ai_article_popup_saves_its_answer_as_before(held, client, user, book):
    client.force_login(user)
    preferences = LanguagePreferences.get_or_create_language_preferences(
        user=user, language=book.language
    )
    preferences.inline_translation_type = "Translate"
    preferences.inline_translation_parameters = {"model": "gpt", "effort": "low"}
    preferences.save()

    with patch("lexiflux.views.lexical_views.generate_article", return_value="страница"):
        _get(client, book, "2")

    assert _entry(user) == ("страница", False)
    assert held == []


@allure.epic("Vocabulary")
@allure.feature("History translation")
def test_background_work_runs_in_its_own_thread_and_closes_its_connection():
    release, done = threading.Event(), threading.Event()
    ran_in, closed_in = [], []

    def work():
        release.wait(5)
        ran_in.append(threading.current_thread())
        done.set()

    connection = MagicMock()
    connection.close.side_effect = lambda: closed_in.append(threading.current_thread())
    with (
        override_settings(HISTORY_TRANSLATION_IN_BACKGROUND=True),
        patch.object(lexical_views, "connection", connection),
    ):
        lexical_views.in_background(work)
        assert not done.is_set()
        release.set()
        assert done.wait(5)
        ran_in[0].join(5)

    assert ran_in[0] is not threading.current_thread()
    assert ran_in[0].daemon
    assert closed_in == ran_in


@allure.epic("Vocabulary")
@allure.feature("History translation")
def test_tests_run_background_work_inline():
    ran_in = []

    lexical_views.in_background(lambda: ran_in.append(threading.current_thread()))

    assert ran_in == [threading.current_thread()]


@allure.epic("Vocabulary")
@allure.feature("History translation")
def test_failing_background_work_is_logged_and_closes_its_connection(caplog):
    def work():
        raise ProcessLookupError("broken")

    connection = MagicMock()
    with patch.object(lexical_views, "connection", connection):
        lexical_views._closing_connection(work)

    assert "Background work failed" in caplog.text
    connection.close.assert_called_once_with()
