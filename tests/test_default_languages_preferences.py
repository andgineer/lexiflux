import allure
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from lexiflux.language.translation import AVAILABLE_TRANSLATORS
from lexiflux.language_preferences_default import add_language_pair_articles
from lexiflux.models import LanguagePreferences, Language, LexicalArticle
from django.db.models.signals import post_save
from django.db.models import QuerySet
from lexiflux.signals import create_language_preferences


@allure.epic("User")
@allure.feature("Language Preferences")
@pytest.mark.django_db
class TestUserSignals:
    def test_language_preferences_created_on_user_creation(self, db_init):
        """Test that language preferences are created when a new user is created."""
        User = get_user_model()

        # Create a new user
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        # Check if language preferences were created
        assert user.default_language_preferences is not None
        assert isinstance(user.default_language_preferences, LanguagePreferences)

        # Check if preferences are properly configured
        preferences = user.default_language_preferences
        assert preferences.user == user
        assert preferences.language is not None
        assert isinstance(preferences.language, Language)

        # Check if the preferences are in the database
        assert LanguagePreferences.objects.filter(user=user).exists()

    def test_signal_creates_complete_language_preferences(self, db_init):
        """Test that created language preferences have all required attributes and lexical articles."""
        User = get_user_model()

        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        preferences = user.default_language_preferences
        assert preferences is not None

        # Check all important attributes
        assert preferences.inline_translation_type is not None
        assert preferences.inline_translation_parameters is not None
        assert isinstance(preferences.inline_translation_parameters, dict)

        # Verify we can get lexical articles
        articles = preferences.get_lexical_articles()
        assert isinstance(articles, QuerySet)
        assert articles.model is LexicalArticle

        # Verify we have lexical articles and they have required fields
        articles_list = list(articles)
        assert len(articles_list) > 0

        for article in articles_list:
            assert isinstance(article, LexicalArticle)
            assert article.language_preferences == preferences
            assert article.type is not None
            assert article.title is not None
            assert isinstance(article.parameters, dict)
            assert isinstance(article.order, int)

    def test_language_preferences_not_duplicated_on_user_update(self, db_init):
        """Test that language preferences aren't duplicated when user is updated."""
        User = get_user_model()

        # Create initial user
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        initial_preferences = user.default_language_preferences
        initial_preferences_count = LanguagePreferences.objects.count()

        # Update the user
        user.email = "newemail@example.com"
        user.save()

        # Check that no new preferences were created
        assert LanguagePreferences.objects.count() == initial_preferences_count
        assert user.default_language_preferences == initial_preferences

    @pytest.fixture
    def disconnect_signals(self):
        """Fixture to temporarily disconnect and reconnect the signal."""
        # Disconnect the signal
        post_save.disconnect(create_language_preferences, sender=get_user_model())
        yield
        # Reconnect the signal after the test
        post_save.connect(create_language_preferences, sender=get_user_model())

    def test_no_language_preferences_created_when_signal_disconnected(
        self, db_init, disconnect_signals
    ):
        """Test that no language preferences are created when the signal is disconnected."""
        User = get_user_model()

        # Create a new user with disconnected signal
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        # Check that no language preferences were created
        assert user.default_language_preferences is None
        assert not LanguagePreferences.objects.filter(user=user).exists()


@allure.epic("User")
@allure.feature("Language Preferences")
@pytest.mark.django_db
def test_new_user_gets_the_default_articles_and_inline_translation(db_init):
    user = get_user_model().objects.create_user(
        username="defaults", email="defaults@example.com", password="testpass123"
    )
    preferences = user.default_language_preferences

    articles = [
        (article.title, article.type, article.parameters)
        for article in preferences.get_lexical_articles()
    ]
    assert articles == [
        ("Article", "AI dictionary", {"model": "pool"}),
        ("In depth", "In depth", {"model": "gpt", "effort": "none", "tier": "priority"}),
        ("Sentence", "Sentence", {"model": "gpt", "effort": "none", "tier": "priority"}),
        (
            "glosbe",
            "Site",
            {"url": "https://glosbe.com/{langCode}/{toLangCode}/{term}", "window": True},
        ),
    ]
    assert preferences.inline_translation_type == "Dictionary"
    assert preferences.inline_translation_parameters == {"dictionary": "LLMTranslation"}
    assert next(iter(AVAILABLE_TRANSLATORS)) == "LLMTranslation"


@allure.epic("User")
@allure.feature("Language Preferences")
@pytest.mark.django_db
def test_default_articles_pass_validation(db_init):
    user = get_user_model().objects.create_user(
        username="valid", email="valid@example.com", password="testpass123"
    )
    for article in user.default_language_preferences.get_lexical_articles():
        article.full_clean()


@allure.epic("User")
@allure.feature("Language Preferences")
@pytest.mark.django_db
def test_preferences_for_another_language_copy_defaults_in_order(db_init):
    user = get_user_model().objects.create_user(
        username="copy", email="copy@example.com", password="testpass123"
    )
    french = Language.objects.get(name="French")
    copied = LanguagePreferences.get_or_create_language_preferences(user, french)
    assert [a.title for a in copied.get_lexical_articles()] == [
        "Article",
        "In depth",
        "Sentence",
        "glosbe",
    ]


LINGEA = (
    "lingea",
    "Site",
    {"url": "https://recnici.lingea.rs/{toLangLingea}-srpski/{termLatin}", "window": True},
)


def _articles(preferences):
    return [
        (article.title, article.type, article.parameters)
        for article in preferences.get_lexical_articles()
    ]


@allure.epic("User")
@allure.feature("Language Preferences")
@pytest.mark.django_db
@pytest.mark.parametrize("user_language", ["ru", "en", "de"])
def test_serbian_for_a_reader_of_a_lingea_language_gets_lingea_after_glosbe(db_init, user_language):
    user = get_user_model().objects.create_user(
        username="lingea",
        email="lingea@example.com",
        password="testpass123",
        language=Language.objects.get(google_code=user_language),
    )

    articles = _articles(user.default_language_preferences)

    assert [title for title, *_ in articles] == [
        "Article",
        "In depth",
        "Sentence",
        "glosbe",
        "lingea",
    ]
    assert articles[-1] == LINGEA


@allure.epic("User")
@allure.feature("Language Preferences")
@pytest.mark.django_db
@pytest.mark.parametrize("user_language", [None, "ka"])
def test_serbian_for_other_readers_has_no_lingea(db_init, user_language):
    user = get_user_model().objects.create_user(
        username="other",
        email="other@example.com",
        password="testpass123",
        language=Language.objects.get(google_code=user_language) if user_language else None,
    )

    assert "lingea" not in [title for title, *_ in _articles(user.default_language_preferences)]


@allure.epic("User")
@allure.feature("Language Preferences")
@pytest.mark.django_db
def test_serbian_preferences_copied_for_a_russian_reader_get_lingea(db_init):
    user = get_user_model().objects.create_user(
        username="copy-ru", email="copy-ru@example.com", password="testpass123"
    )
    serbian = user.default_language_preferences
    german = LanguagePreferences.get_or_create_language_preferences(
        user, Language.objects.get(google_code="de")
    )
    german.user_language = Language.objects.get(google_code="ru")
    german.save()
    user.default_language_preferences = german
    user.save()
    serbian.delete()

    copied = LanguagePreferences.get_or_create_language_preferences(
        user, Language.objects.get(google_code="sr")
    )

    assert [title for title, *_ in _articles(copied)] == [
        "Article",
        "In depth",
        "Sentence",
        "glosbe",
        "lingea",
    ]
    assert "lingea" not in [title for title, *_ in _articles(german)]


@allure.epic("User")
@allure.feature("Language Preferences")
@pytest.mark.django_db
def test_lingea_is_not_added_twice(db_init):
    user = get_user_model().objects.create_user(
        username="twice",
        email="twice@example.com",
        password="testpass123",
        language=Language.objects.get(google_code="ru"),
    )
    preferences = user.default_language_preferences
    preferences.lexical_articles.filter(title="lingea").update(title="my lingea")

    add_language_pair_articles(preferences)

    assert [title for title, *_ in _articles(preferences)][-1] == "my lingea"
    assert len(_articles(preferences)) == 5


@allure.epic("User")
@allure.feature("Language Preferences")
@pytest.mark.django_db
def test_an_unknown_dictionary_does_not_validate(db_init):
    user = get_user_model().objects.create_user(
        username="unknown", email="unknown@example.com", password="testpass123"
    )
    preferences = user.default_language_preferences
    article = LexicalArticle(
        language_preferences=preferences,
        type="Dictionary",
        title="Old",
        parameters={"dictionary": "MyMemoryTranslator"},
    )

    with pytest.raises(ValidationError, match="Unknown dictionary 'MyMemoryTranslator'"):
        article.full_clean()
    preferences.inline_translation_parameters = {"dictionary": "GoogleTranslator"}
    with pytest.raises(ValidationError, match="Unknown dictionary 'GoogleTranslator'"):
        preferences.save()
    for dictionary in AVAILABLE_TRANSLATORS:
        article.parameters = {"dictionary": dictionary}
        article.full_clean()


@allure.epic("User")
@allure.feature("Language Preferences")
@pytest.mark.django_db
def test_other_languages_copied_from_serbian_for_a_russian_reader_have_no_lingea(db_init):
    user = get_user_model().objects.create_user(
        username="en-ru",
        email="en-ru@example.com",
        password="testpass123",
        language=Language.objects.get(google_code="ru"),
    )

    english = LanguagePreferences.get_or_create_language_preferences(
        user, Language.objects.get(google_code="en")
    )

    assert [title for title, *_ in _articles(english)] == [
        "Article",
        "In depth",
        "Sentence",
        "glosbe",
    ]
    assert _articles(user.default_language_preferences)[-1] == LINGEA
