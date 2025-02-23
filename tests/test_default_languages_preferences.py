import allure
import pytest
from django.contrib.auth import get_user_model
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
