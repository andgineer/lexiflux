import pytest
import allure
from unittest.mock import patch, MagicMock, PropertyMock, Mock
from lexiflux.models import BookPage, Book, TranslationHistory, AIModelConfig
from lexiflux.language.llm import (
    Llm,
    AIModelError,
    _remove_word_marks,
    _remove_sentence_marks,
    _extract_sentence,
    find_nth_occurrence,
    safe_float,
    TextOutputParser,
)
from lexiflux.language.sentence_extractor_llm import (
    SENTENCE_START_MARK,
    SENTENCE_END_MARK,
    WORD_START_MARK,
    WORD_END_MARK,
)
from lexiflux.views.lexical_views import get_context_for_translation_history


@pytest.fixture
def mock_book_page(book):
    page = BookPage.objects.get(book=book, number=1)
    content = "Word1 word2. Word3 word4. Word5 word6 word7. Word8 word9. Word10 word11 word12."

    words_cache = [
        (0, 5),
        (6, 11),
        (13, 18),
        (19, 24),
        (26, 31),  # 0 - 4
        (32, 37),
        (38, 43),
        (45, 50),
        (51, 56),
        (58, 64),  # 5 - 9
        (65, 71),
        (72, 78),
    ]

    word_sentence_mapping_cache = {
        0: 0,
        1: 0,
        2: 1,
        3: 1,
        4: 2,
        5: 2,
        6: 2,
        7: 3,
        8: 3,
        9: 4,
        10: 4,
        11: 4,
    }

    with (
        patch("lexiflux.models.BookPage.words", new_callable=PropertyMock) as mock_words,
        patch(
            "lexiflux.models.BookPage.word_sentence_mapping", new_callable=PropertyMock
        ) as mock_word_sentence_mapping,
        patch("lexiflux.models.BookPage.content", new_callable=PropertyMock) as mock_content,
    ):
        mock_words.return_value = words_cache
        mock_word_sentence_mapping.return_value = word_sentence_mapping_cache
        mock_content.return_value = content
        yield page


@pytest.fixture
def llm_instance():
    return Llm()


@allure.epic("Language Tools")
@allure.feature("Term and Sentence Marking")
def test_mark_term_and_sentence_success(mock_book_page, llm_instance):
    # Prepare test data
    data = {
        "book_code": mock_book_page.book.code,
        "book_page_number": mock_book_page.number,
        "term_word_ids": [4, 5],  # "Word5 word6"
    }

    # Call the method
    result = llm_instance.mark_term_and_sentence(llm_instance.hashable_dict(data), context_words=2)

    expected_result = (
        f"Word3 word4. {SENTENCE_START_MARK}{WORD_START_MARK}Word5 word6{WORD_END_MARK} "
        f"word7{SENTENCE_END_MARK}. Word8 word9"
    )

    assert result == expected_result

    # Test with different term and context
    data["term_word_ids"] = [9, 10]  # "Word10 word11"
    result = llm_instance.mark_term_and_sentence(llm_instance.hashable_dict(data), context_words=3)

    expected_result = (
        f"Word5 word6 word7. Word8 word9. {SENTENCE_START_MARK}{WORD_START_MARK}Word10 "
        f"word11{WORD_END_MARK} word12{SENTENCE_END_MARK}"
    )

    assert result == expected_result


@allure.epic("Language Tools")
@allure.feature("Term and Sentence Marking")
@pytest.mark.parametrize(
    "term_word_ids, expected_term",
    [
        ([0, 1], "Word1 word2"),
        ([4, 5], "Word5 word6"),
        ([9, 10, 11], "Word10 word11 word12"),
    ],
)
def test_mark_term_and_sentence_different_terms(
    mock_book_page, llm_instance, term_word_ids, expected_term
):
    data = {
        "book_code": mock_book_page.book.code,
        "book_page_number": mock_book_page.number,
        "term_word_ids": term_word_ids,
    }

    result = llm_instance.mark_term_and_sentence(llm_instance.hashable_dict(data), context_words=2)
    print(f"Marked text for term '{expected_term}': {result}")

    assert f"{WORD_START_MARK}{expected_term}{WORD_END_MARK}" in result


@allure.epic("Language Tools")
@allure.feature("Term and Sentence Marking")
@pytest.mark.parametrize(
    "context_words, expected_words_before, expected_words_after",
    [
        (1, 2, 0),  # include word4(+3 in the same sentence) and word7 (in the same sentence as term
        (2, 2, 3),  # include word3 and word8 (+9 in the same sentence)
        (5, 4, 6),  # include word1 and word11 (plus ".")
    ],
)
def test_mark_term_and_sentence_different_context(
    mock_book_page, llm_instance, context_words, expected_words_before, expected_words_after
):
    data = {
        "book_code": mock_book_page.book.code,
        "book_page_number": mock_book_page.number,
        "term_word_ids": [4, 5],  # "Word5 word6"
    }

    result = (
        llm_instance.mark_term_and_sentence(
            llm_instance.hashable_dict(data), context_words=context_words
        )
        .replace(WORD_START_MARK, "")
        .replace(WORD_END_MARK, "")
    )
    print(f"Marked text with context_words={context_words}: {result}")

    words_before = result.split(SENTENCE_START_MARK)[0].split()
    words_after = result.split(SENTENCE_END_MARK)[1].split()

    assert len(words_before) == expected_words_before
    assert len(words_after) == expected_words_after


@pytest.fixture
def mock_llm():
    with patch("lexiflux.views.lexical_views.Llm") as mock:
        yield mock


@allure.epic("Language Tools")
@allure.feature("Term and Sentence Marking")
def test_get_context_for_translation_history(mock_llm):
    # Setup
    book = Mock(spec=Book)
    book.code = "TEST_BOOK"
    book_page = Mock(spec=BookPage)
    book_page.number = 42
    term_word_ids = [1, 2, 3]

    # Configure mock
    mock_llm_instance = mock_llm.return_value
    mock_llm_instance.hashable_dict.return_value = {
        "book_code": "TEST_BOOK",
        "book_page_number": 42,
        "term_word_ids": [1, 2, 3],
    }
    mock_llm_instance.mark_term_and_sentence.return_value = f"Some context {SENTENCE_START_MARK}This is a {WORD_START_MARK}test{WORD_END_MARK} sentence.{SENTENCE_END_MARK} More context."

    # Call the function
    result = get_context_for_translation_history(book, book_page, term_word_ids)

    # Assertions
    expected_result = f"Some context {TranslationHistory.CONTEXT_MARK}This is a {TranslationHistory.CONTEXT_MARK} sentence.{TranslationHistory.CONTEXT_MARK} More context."
    assert result == expected_result

    # Verify mock calls
    mock_llm_instance.hashable_dict.assert_called_once_with(
        {
            "book_code": "TEST_BOOK",
            "book_page_number": 42,
            "term_word_ids": [1, 2, 3],
        }
    )
    mock_llm_instance.mark_term_and_sentence.assert_called_once_with(
        mock_llm_instance.hashable_dict.return_value, context_words=10
    )


@allure.epic("Language Tools")
@allure.feature("Term and Sentence Marking")
def test_get_context_for_translation_history_error_handling(mock_llm):
    # Setup
    book = Mock(spec=Book)
    book_page = Mock(spec=BookPage)
    term_word_ids = [1, 2, 3]

    # Configure mock to raise an exception
    mock_llm_instance = mock_llm.return_value
    mock_llm_instance.mark_term_and_sentence.side_effect = Exception("LLM error")

    # Call the function and check for exception
    with pytest.raises(Exception, match="LLM error"):
        get_context_for_translation_history(book, book_page, term_word_ids)


@allure.epic("Language Tools")
@allure.feature("Term Detection")
class TestTermDetection:
    @pytest.mark.parametrize(
        "text,term,occurrence,expected",
        [
            (
                "The cat sat on the mat. The cat ran.",
                "cat",
                1,
                {
                    "term_word_ids": [1],
                    "word_slices": [
                        (0, 3),
                        (4, 7),
                        (8, 11),
                        (12, 14),
                        (15, 18),
                        (19, 22),
                        (24, 27),
                        (28, 31),
                        (32, 35),
                    ],
                },
            ),
            (
                "The cat sat on the mat. The cat ran.",
                "cat",
                2,
                {
                    "term_word_ids": [7],
                    "word_slices": [
                        (0, 3),
                        (4, 7),
                        (8, 11),
                        (12, 14),
                        (15, 18),
                        (19, 22),
                        (24, 27),
                        (28, 31),
                        (32, 35),
                    ],
                },
            ),
        ],
    )
    def test_detect_term_words(self, text, term, occurrence, expected):
        llm = Llm()
        result = llm.detect_term_words(text, term, occurrence)
        assert result["term_word_ids"] == expected["term_word_ids"]
        assert len(result["word_slices"]) == len(expected["word_slices"])


@allure.epic("Language Tools")
@allure.feature("Model Settings")
class TestModelSettings:
    def test_get_model_settings_with_user_config(self, db_init, approved_user):
        llm = Llm()
        model_class = "ChatOpenAI"

        # Create mock AIModelConfig with a real Django user
        config = AIModelConfig(
            user=approved_user,  # Use the approved_user fixture
            chat_model=model_class,
            settings={"api_key": "test_key", "temperature": 0.7},
        )

        with patch(
            "lexiflux.models.AIModelConfig.get_or_create_ai_model_config", return_value=config
        ):
            settings = llm.get_model_settings(approved_user, model_class)
            assert settings["api_key"] == "test_key"
            assert settings["temperature"] == 0.7

    def test_get_model_settings_from_db(self, db_init, approved_user):
        llm = Llm()
        model_class = "ChatOpenAI"

        # Create mock AIModelConfig with settings
        config = AIModelConfig(
            user=approved_user,  # Use the approved_user fixture
            chat_model=model_class,
            settings={"temperature": 0.7, "api_key": "db_key"},
        )

        with patch(
            "lexiflux.models.AIModelConfig.get_or_create_ai_model_config", return_value=config
        ):
            settings = llm.get_model_settings(approved_user, model_class)
            assert settings["temperature"] == 0.7
            assert settings["api_key"] == "db_key"


@allure.epic("Language Tools")
@allure.feature("Model Management")
class TestModelManagement:
    def test_get_or_create_model_openai(self, request, approved_user):
        llm = Llm()
        params = {"model": "gpt-5", "user": approved_user}

        mock_settings = {"api_key": "test_key", "temperature": 0.7}
        with patch.object(Llm, "get_model_settings", return_value=mock_settings):
            if request.config.getoption("--use-llm"):
                model = llm._get_or_create_model(params)
                assert model is not None
            else:
                mock_chat = MagicMock()
                with patch(
                    "lexiflux.language.llm.ChatOpenAI", return_value=mock_chat
                ) as mock_openai:
                    model = llm._get_or_create_model(params)

                    # Verify the model was created with correct parameters
                    mock_openai.assert_called_once_with(
                        model="gpt-5", api_key="test_key", temperature=0.7
                    )
                    assert model is mock_chat

    def test_get_or_create_model_invalid(self, approved_user):
        llm = Llm()
        params = {"model": "invalid_model", "user": approved_user}

        with pytest.raises(ValueError, match="Unsupported model"):
            llm._get_or_create_model(params)


@allure.epic("Language Tools")
@allure.feature("Article Generation")
class TestArticleGeneration:
    @pytest.mark.parametrize(
        "article_name,expected_prompt_file",
        [
            ("Translate", "Translate.txt"),
            ("Lexical", "Lexical.txt"),
            ("Explain", "Explain.txt"),
            ("Origin", "Origin.txt"),
            ("Sentence", "Sentence.txt"),
            ("Origin", "Origin.txt"),
        ],
    )
    def test_generate_article_cached_with_different_articles(
        self,
        request,
        mock_book_page,
        llm_instance,
        approved_user,
        article_name,
        expected_prompt_file,
    ):
        # Prepare test data
        params = {"model": "gpt-5", "user": approved_user}
        data = {
            "book_code": mock_book_page.book.code,
            "book_page_number": mock_book_page.number,
            "term_word_ids": [4, 5],  # "Word5 word6"
            "text_language": "en",
            "user_language": "fr",
        }

        # Read expected prompt
        import os
        from django.conf import settings

        prompt_path = os.path.join(
            settings.BASE_DIR, "lexiflux", "resources", "prompts", expected_prompt_file
        )
        with open(prompt_path, "r", encoding="utf8") as f:
            expected_prompt = f.read().strip()

        # Expected response from the AI model
        expected_response = "AI generated response"

        if request.config.getoption("--use-llm"):
            # Use real LLM
            result = llm_instance._generate_article_cached(
                article_name, llm_instance.hashable_dict(params), llm_instance.hashable_dict(data)
            )
            assert isinstance(result, str)
            assert len(result) > 0
        else:
            # Mock the AI model responses
            mock_chat = MagicMock()
            mock_chat.invoke.return_value = expected_response

            # Create a pipeline that mimics langchain's behavior
            class MockPipeline:
                def __init__(self, response):
                    self.response = response

                def invoke(self, *args, **kwargs):
                    return self.response

            mock_pipeline = MockPipeline(expected_response)

            # Mock the factory function to return our pipeline
            original_factory = llm_instance._article_pipelines_factory[article_name]
            llm_instance._article_pipelines_factory[article_name] = lambda model: mock_pipeline

            try:
                with patch(
                    "lexiflux.language.llm.ChatOpenAI", return_value=mock_chat
                ) as mock_openai:
                    # Call the method
                    result = llm_instance._generate_article_cached(
                        article_name,
                        llm_instance.hashable_dict(params),
                        llm_instance.hashable_dict(data),
                    )

                    # Verify the result
                    assert result == expected_response

                    # Verify ChatOpenAI was initialized correctly
                    mock_openai.assert_called_once()
                    call_kwargs = mock_openai.call_args.kwargs
                    assert call_kwargs["model"] == "gpt-5"
                    assert "temperature" in call_kwargs
            finally:
                # Restore the original factory function
                llm_instance._article_pipelines_factory[article_name] = original_factory

    def test_generate_article_cached_ai_type(
        self, request, mock_book_page, llm_instance, approved_user
    ):
        # Prepare test data
        params = {
            "model": "gpt-5",
            "user": approved_user,
            "prompt": "Custom system prompt for AI article",
        }
        data = {
            "book_code": mock_book_page.book.code,
            "book_page_number": mock_book_page.number,
            "term_word_ids": [4, 5],
            "text_language": "en",
            "user_language": "fr",
        }

        expected_response = "AI generated response for custom prompt"

        if request.config.getoption("--use-llm"):
            # Use real LLM
            result = llm_instance._generate_article_cached(
                "AI", llm_instance.hashable_dict(params), llm_instance.hashable_dict(data)
            )
            assert isinstance(result, str)
            assert len(result) > 0
        else:
            # Mock the AI model and its response
            mock_chat = MagicMock()
            mock_chat.invoke.return_value = "AI generated response for custom prompt"

            # Create a pipeline that mimics langchain's behavior
            class MockPipeline:
                def __init__(self, response):
                    self.response = response

                def invoke(self, messages):
                    return self.response

            mock_pipeline = MockPipeline(expected_response)

            # Mock the factory function
            original_factory = llm_instance._article_pipelines_factory["AI"]
            llm_instance._article_pipelines_factory["AI"] = lambda model: mock_pipeline

            try:
                with patch(
                    "lexiflux.language.llm.ChatOpenAI", return_value=mock_chat
                ) as mock_openai:
                    result = llm_instance._generate_article_cached(
                        "AI", llm_instance.hashable_dict(params), llm_instance.hashable_dict(data)
                    )

                    # Verify the result
                    assert result == expected_response

                    # Verify ChatOpenAI was initialized correctly
                    mock_openai.assert_called_once()
                    call_kwargs = mock_openai.call_args.kwargs
                    assert call_kwargs["model"] == "gpt-5"
                    assert "temperature" in call_kwargs
            finally:
                # Restore the original factory function
                llm_instance._article_pipelines_factory["AI"] = original_factory

    def test_generate_article_cached_invalid_article(self, llm_instance, approved_user):
        # Prepare test data
        params = {"model": "gpt-5", "user": approved_user}
        data = {"text": "Sample text", "text_language": "en", "user_language": "fr"}

        with pytest.raises(ValueError, match="Lexical article 'InvalidArticle' not found"):
            llm_instance._generate_article_cached(
                "InvalidArticle",
                llm_instance.hashable_dict(params),
                llm_instance.hashable_dict(data),
            )

    def test_generate_article_error_handling(self, approved_user):
        llm = Llm()
        article_name = "Translate"
        params = {"model": "gpt-5", "user": approved_user}
        data = {"text": "Test text"}

        with patch.object(Llm, "_generate_article_cached", side_effect=Exception("Test error")):
            with pytest.raises(AIModelError) as exc_info:
                llm.generate_article(article_name, params, data)

            assert exc_info.value.model_name == "gpt-5"
            assert "Test error" in str(exc_info.value)

    def test_generate_article_invalid_article(self):
        llm = Llm()
        article_name = "InvalidArticle"
        params = {"model": "gpt-5", "user": MagicMock()}
        data = {"text": "Test text"}

        with pytest.raises(AIModelError) as exc_info:
            llm.generate_article(article_name, params, data)

        assert "AI insight 'InvalidArticle' not found" in str(exc_info.value)

    @patch("lexiflux.language.llm.ChatOpenAI")
    def test_generate_article_api_error(self, mock_chat_openai, approved_user, book):
        llm = Llm()
        article_name = "Translate"
        params = {"model": "gpt-5", "user": approved_user}
        data = {
            "text": "Test text",
            "text_language": "en",
            "user_language": "fr",
            # "book_code": "some-book-code",
            "book_page_number": 2,
            "term_word_ids": [1, 2, 3],
        }

        # Simulate an API error
        mock_chat_openai.side_effect = ValueError("API Error")

        with pytest.raises(AIModelError) as exc_info:
            llm.generate_article(article_name, params, data)

        assert "'book_code'" in str(exc_info.value)
        assert exc_info.value.model_name == "gpt-5"


@allure.epic("Language Tools")
@allure.feature("Text Processing")
class TestTextProcessing:
    @pytest.mark.parametrize(
        "text, expected",
        [
            (f"{WORD_START_MARK}test{WORD_END_MARK}", "test"),
            (f"before {WORD_START_MARK}test{WORD_END_MARK} after", "before test after"),
        ],
    )
    def test_remove_word_marks(self, text, expected):
        assert _remove_word_marks(text) == expected

    @pytest.mark.parametrize(
        "text, expected",
        [
            (f"{SENTENCE_START_MARK}test{SENTENCE_END_MARK}", "test"),
            (f"before {SENTENCE_START_MARK}test{SENTENCE_END_MARK} after", "before test after"),
        ],
    )
    def test_remove_sentence_marks(self, text, expected):
        assert _remove_sentence_marks(text) == expected

    @pytest.mark.parametrize(
        "text, expected",
        [
            (f"before {SENTENCE_START_MARK}test{SENTENCE_END_MARK} after", "test"),
            (f"{SENTENCE_START_MARK}test{SENTENCE_END_MARK}", "test"),
            (
                f"{WORD_START_MARK}word{WORD_END_MARK} in {SENTENCE_START_MARK}sentence{SENTENCE_END_MARK}",
                "sentence",
            ),
        ],
    )
    def test_extract_sentence(self, text, expected):
        assert _extract_sentence(text) == expected


@allure.epic("Language Tools")
@allure.feature("Utility Functions")
class TestUtilityFunctions:
    @pytest.mark.parametrize(
        "text, substring, occurrence, expected",
        [
            ("hello hello hello", "hello", 1, 0),
            ("hello hello hello", "hello", 2, 6),
            ("hello hello hello", "hello", 3, 12),
            ("hello hello hello", "hello", 4, -1),
            ("test text", "missing", 1, -1),
        ],
    )
    def test_find_nth_occurrence(self, text, substring, occurrence, expected):
        assert find_nth_occurrence(substring, text, occurrence) == expected

    @pytest.mark.parametrize(
        "value, expected",
        [
            (0.7, 0.7),
            ("0.7", 0.7),
            (None, 0.5),
            ("invalid", 0.5),
        ],
    )
    def test_safe_float(self, value, expected):
        assert safe_float(value) == expected

    def test_text_output_parser(self):
        parser = TextOutputParser()
        text = f"{WORD_START_MARK}word{WORD_END_MARK} in {SENTENCE_START_MARK}sentence{SENTENCE_END_MARK}"
        expected = "word in sentence"
        assert parser.parse(text) == expected


@allure.epic("Language Tools")
@allure.feature("Error Handling")
class TestErrorHandling:
    def test_ai_model_error(self):
        error = AIModelError("gpt-5", "ChatOpenAI", "API error")
        assert error.model_name == "gpt-5"
        assert error.model_class == "ChatOpenAI"
        assert error.error_message == "API error"
        assert str(error) == "AI class `ChatOpenAI` error for model `gpt-5`: API error"
