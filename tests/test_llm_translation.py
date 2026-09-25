import json
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch

import allure
import pytest
from django.urls import reverse
from llmbroker import (
    AuthError,
    LLMTimeoutError,
    NoLLMAvailableError,
    ProviderError,
    RateLimitError,
)

from lexiflux.language import llm
from lexiflux.language.llm import (
    INLINE_TRANSLATION_SECONDS,
    ArticleError,
    InlineTranslationRequest,
    translate_inline,
)
from lexiflux.language.translation import (
    GoogleTranslator,
    LLMTranslator,
    Term,
    Translator,
    WiktionaryTranslator,
)
from lexiflux.models import Language, LanguagePreferences, LexicalArticle, TranslationHistory

PASSAGE = (
    "The old armchair had seen better days. When Tom sat down, a ⟦spring⟧ creaked deep "
    "inside the seat. He jumped up at once."
)
RAW_ERROR_TEXT = "raw-secret-detail"


class FakePool:
    def __init__(self, *answers):
        self.answers = list(answers)
        self.calls = []

    def ask(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        answer = self.answers.pop(0)
        if isinstance(answer, threading.Event):
            assert answer.wait(10), "the test never released the stalled answer"
            answer = "поздно"
        if isinstance(answer, BaseException):
            raise answer
        return SimpleNamespace(text=answer)


@pytest.fixture
def pool():
    holder = {"pool": FakePool("пружина")}
    with patch("lexiflux.language.llm.llms_for", side_effect=lambda user: holder["pool"]):
        yield holder


def inline_request(**changes):
    values = {
        "word": "spring",
        "passage": PASSAGE,
        "text_language": "English",
        "user_language": "Russian",
        "user": SimpleNamespace(id=7),
    } | changes
    return InlineTranslationRequest(**values)


@allure.epic("Translators")
@allure.feature("LLM translation")
class TestTranslateInline:
    def test_answer_is_the_pool_text_stripped(self, pool):
        pool["pool"] = FakePool(" пружина \n")

        assert translate_inline(inline_request()) == "пружина"

    def test_free_pool_races_two_models_within_the_limit(self, pool):
        translate_inline(inline_request())

        (_, kwargs), *_ = pool["pool"].calls
        assert kwargs == {"operation": "Inline translation", "fastest_of": 2, "wait": 3.0}
        assert INLINE_TRANSLATION_SECONDS == 3.0

    def test_prompt_has_the_marked_passage_and_language_names(self, pool):
        translate_inline(inline_request(text_language="German", user_language="Serbian"))

        prompt = pool["pool"].calls[0][0]
        assert prompt.startswith(
            "Translate the German word or phrase marked with ⟦ ⟧ into Serbian, in the sense"
        )
        assert "separable verb or a fixed expression, translate the whole unit" in prompt
        assert "Reply with only the Serbian translation in dictionary form" in prompt
        assert prompt.endswith(f"Text: {PASSAGE}")
        assert "⟦spring⟧" in prompt
        assert "{" not in prompt and "}" not in prompt

    def test_cache_hit_asks_nothing_and_is_shared_by_users(self, pool):
        translate_inline(inline_request())
        pool["pool"] = FakePool("другое")

        assert translate_inline(inline_request()) == "пружина"
        assert translate_inline(inline_request(user=SimpleNamespace(id=8))) == "пружина"
        assert pool["pool"].calls == []

    @pytest.mark.parametrize(
        "change",
        [
            {"passage": "An early ⟦spring⟧ came."},
            {"word": "Spring"},
            {"text_language": "German"},
            {"user_language": "Serbian"},
        ],
        ids=["passage", "word", "text language", "user language"],
    )
    def test_cache_key_is_word_passage_and_languages(self, pool, change):
        translate_inline(inline_request())
        pool["pool"] = FakePool("другое")

        assert translate_inline(inline_request(**change)) == "другое"

    def test_failure_is_not_cached(self, pool):
        pool["pool"] = FakePool(NoLLMAvailableError("none", reason="timeout"), "пружина")

        with pytest.raises(ArticleError):
            translate_inline(inline_request())
        assert translate_inline(inline_request()) == "пружина"
        assert len(pool["pool"].calls) == 2

    def test_empty_answer_is_not_cached(self, pool):
        pool["pool"] = FakePool("  ", "пружина")

        assert translate_inline(inline_request()) == ""
        assert translate_inline(inline_request()) == "пружина"

    @pytest.mark.parametrize(
        "error, kind",
        [
            (NoLLMAvailableError("none", reason="no_keys"), ArticleError.NO_KEYS),
            (NoLLMAvailableError("none", reason="timeout"), ArticleError.BUSY),
            (RateLimitError("slow down", status=429, retry_after=12), ArticleError.BUSY),
            (LLMTimeoutError("wait ran out"), ArticleError.BUSY),
            (AuthError("rejected", status=401), ArticleError.AUTH),
            (ProviderError(RAW_ERROR_TEXT, status=500), ArticleError.GENERIC),
        ],
        ids=["no keys", "pool timeout", "rate limit", "llm timeout", "auth", "other"],
    )
    def test_llmbroker_errors_become_article_errors(self, pool, error, kind):
        pool["pool"] = FakePool(error)

        with pytest.raises(ArticleError) as raised:
            translate_inline(inline_request())

        assert raised.value.kind == kind
        assert raised.value.html.startswith("<div")
        assert RAW_ERROR_TEXT not in raised.value.html

    def test_stalled_pool_is_busy_at_the_limit_and_its_late_answer_is_dropped(self, pool):
        stalled = threading.Event()
        pool["pool"] = FakePool(stalled, "пружина")
        try:
            with patch.object(llm, "INLINE_TRANSLATION_SECONDS", 0.2):
                started = time.monotonic()
                with pytest.raises(ArticleError) as raised:
                    translate_inline(inline_request())
                elapsed = time.monotonic() - started
        finally:
            stalled.set()

        assert raised.value.kind == ArticleError.BUSY
        assert 0.2 <= elapsed < 1.0
        assert translate_inline(inline_request()) == "пружина"


@allure.epic("Translators")
@allure.feature("LLM translation")
def test_llm_translation_is_a_registered_translator(pool):
    translator = Translator("LLMTranslation", "English", "Russian")
    user = SimpleNamespace(id=7)

    assert isinstance(translator._translator, LLMTranslator)
    assert {"value": "LLMTranslation", "label": "LLM translation"} in (
        Translator.available_translators()
    )
    assert translator.translate(Term("spring", PASSAGE, user)) == "пружина"
    prompt = pool["pool"].calls[0][0]
    assert "Translate the English word" in prompt
    assert "into Russian" in prompt


def _preferences(user, book):
    preferences = LanguagePreferences.get_or_create_language_preferences(
        user=user, language=book.language
    )
    preferences.user_language = Language.objects.get(name="Russian")
    preferences.inline_translation_type = "Dictionary"
    preferences.inline_translation_parameters = {"dictionary": "LLMTranslation"}
    preferences.save()
    return preferences


def _popup(client, user, book):
    client.force_login(user)
    _preferences(user, book)
    return client.get(
        reverse("translate"),
        {
            "lexical-article": "0",
            "book-code": book.code,
            "book-page-number": "1",
            "word-ids": "2",
        },
    )


@pytest.fixture
def other_translators():
    with (
        patch.object(GoogleTranslator, "translate") as google,
        patch.object(WiktionaryTranslator, "translate") as wiktionary,
    ):
        yield google, wiktionary
    google.assert_not_called()
    wiktionary.assert_not_called()


@allure.epic("Translators")
@allure.feature("LLM translation")
@pytest.mark.django_db
def test_popup_shows_the_translation_and_remembers_it(pool, client, user, book):
    pool["pool"] = FakePool("страница")

    response = _popup(client, user, book)

    assert response.status_code == 200
    assert response.json() == {"article": "страница"}
    assert TranslationHistory.objects.get(user=user, term="page").translation == "страница"
    prompt = pool["pool"].calls[0][0]
    assert prompt.endswith("Text: Content of ⟦page⟧ 1")
    assert "Translate the English word" in prompt
    assert "into Russian" in prompt


@allure.epic("Translators")
@allure.feature("LLM translation")
@pytest.mark.django_db
def test_popup_translation_is_cached(pool, client, user, book):
    pool["pool"] = FakePool("страница")
    _popup(client, user, book)

    response = _popup(client, user, book)

    assert response.json() == {"article": "страница"}
    assert len(pool["pool"].calls) == 1
    assert TranslationHistory.objects.get(user=user, term="page").lookup_count == 2


@allure.epic("Translators")
@allure.feature("LLM translation")
@pytest.mark.django_db
def test_popup_stalled_pool_is_an_alert_after_three_seconds(
    pool, other_translators, client, user, book
):
    stalled = threading.Event()
    pool["pool"] = FakePool(stalled, "страница")
    try:
        started = time.monotonic()
        response = _popup(client, user, book)
        elapsed = time.monotonic() - started
    finally:
        stalled.set()

    assert 3.0 <= elapsed < 4.5
    data = response.json()
    assert data["error"] is True
    assert data["kind"] == ArticleError.BUSY
    assert "The AI models are busy right now" in data["article"]
    assert not TranslationHistory.objects.filter(user=user).exists()
    assert _popup(client, user, book).json() == {"article": "страница"}


@allure.epic("Translators")
@allure.feature("LLM translation")
@pytest.mark.django_db
@pytest.mark.parametrize(
    "error, kind, message",
    [
        (
            NoLLMAvailableError("none", reason="no_keys"),
            ArticleError.NO_KEYS,
            "The free pool needs at least one key",
        ),
        (
            RateLimitError("slow down", status=429, retry_after=12),
            ArticleError.BUSY,
            "Please retry in 12 s",
        ),
        (AuthError("rejected", status=401), ArticleError.AUTH, "Key rejected"),
        (ProviderError(RAW_ERROR_TEXT, status=500), ArticleError.GENERIC, "ProviderError"),
    ],
    ids=["no keys", "busy", "auth", "other"],
)
def test_popup_llmbroker_error_is_an_alert_without_fallback(
    pool, other_translators, error, kind, message, client, user, book, caplog
):
    pool["pool"] = FakePool(error)

    response = _popup(client, user, book)

    data = response.json()
    assert data["error"] is True
    assert data["kind"] == kind
    assert 'class="alert' in data["article"]
    assert message in data["article"]
    assert RAW_ERROR_TEXT not in data["article"]
    assert not TranslationHistory.objects.filter(user=user).exists()
    assert "AI article failed" in caplog.text
    assert "Dictionary article failed" not in caplog.text


@allure.epic("Translators")
@allure.feature("LLM translation")
@pytest.mark.django_db
def test_popup_empty_answer_is_no_translation(pool, other_translators, client, user, book):
    pool["pool"] = FakePool("")

    data = _popup(client, user, book).json()

    assert data["error"] is True
    assert data["kind"] == "not_found"
    assert "LLM translation found no translation." in data["article"]


@allure.epic("Translators")
@allure.feature("LLM translation")
@pytest.mark.django_db
def test_sidebar_dictionary_article_uses_the_llm_translation(pool, client, user, book):
    pool["pool"] = FakePool("<страница>")
    client.force_login(user)
    preferences = _preferences(user, book)
    LexicalArticle.objects.create(
        language_preferences=preferences,
        type="Dictionary",
        title="LLM",
        parameters={"dictionary": "LLMTranslation"},
        order=10,
    )

    response = client.get(
        reverse("translate_stream"),
        {
            "lexical-article": str(preferences.get_lexical_articles().count()),
            "book-code": book.code,
            "book-page-number": "1",
            "word-ids": "2",
        },
    )
    events = [json.loads(line) for line in b"".join(response.streaming_content).splitlines()]

    assert events == [{"event": "delta", "text": "&lt;страница&gt;"}, {"event": "done"}]
