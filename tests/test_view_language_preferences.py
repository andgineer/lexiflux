import json
from unittest.mock import patch, MagicMock

import allure
import pytest
from deep_translator.exceptions import LanguageNotSupportedException
from django.urls import reverse

from lexiflux.language_preferences_default import DEFAULT_LEXICAL_ARTICLES
from lexiflux.models import LanguagePreferences, Language, LexicalArticle


DEFAULT_ARTICLES_NUM = len(DEFAULT_LEXICAL_ARTICLES)  # created in migrations

@allure.epic('Pages endpoints')
@allure.story('Language Preferences')
@pytest.mark.django_db
def test_language_preferences_unauthorized_access(client):
    """Test that unauthorized users are redirected to login."""
    response = client.get(reverse('language-preferences'))
    assert response.status_code == 302
    assert response.url.startswith('/accounts/login')


@allure.epic('Pages endpoints')
@allure.story('Language Preferences')
@pytest.mark.django_db
def test_language_preferences_editor_view(client, approved_user):
    """Test the main language preferences editor view."""
    client.force_login(approved_user)
    response = client.get(reverse('language-preferences'))

    assert response.status_code == 200
    assert 'language-preferences.html' in [t.name for t in response.templates]

    context = response.context
    assert context['user'] == approved_user
    assert 'all_languages' in context
    assert 'articles' in context
    assert 'inline_translation' in context
    assert 'lexical_article_types' in context
    assert 'ai_models' in context
    assert 'translators' in context


@allure.epic('Pages endpoints')
@allure.story('Language Preferences')
@pytest.mark.django_db
def test_get_language_preferences(client, approved_user, language):
    """Test getting language preferences for a specific language."""
    client.force_login(approved_user)

    url = reverse('get_language_preferences')
    data = {'language_id': language.google_code}

    response = client.post(
        url,
        json.dumps(data),
        content_type='application/json'
    )

    assert response.status_code == 200
    response_data = json.loads(response.content)
    assert response_data['status'] == 'success'
    assert 'language_preferences_id' in response_data
    assert 'articles' in response_data
    assert 'inline_translation' in response_data
    assert 'all_languages' in response_data


@allure.epic('Pages endpoints')
@allure.story('Language Preferences')
@pytest.mark.django_db
def test_update_user_language(client, approved_user, language):
    """Test updating user language preferences."""
    client.force_login(approved_user)

    # Create language preferences first
    lang_prefs = LanguagePreferences.get_or_create_language_preferences(
        approved_user, language
    )

    url = reverse('api_update_user_language')
    data = {
        'language_id': language.google_code,
        'language_preferences_language_id': language.google_code
    }

    response = client.post(
        url,
        json.dumps(data),
        content_type='application/json'
    )

    assert response.status_code == 200
    response_data = json.loads(response.content)
    assert response_data['status'] == 'success'

    # Verify the update
    lang_prefs.refresh_from_db()
    assert lang_prefs.user_language == language


@allure.epic('Pages endpoints')
@allure.story('Language Preferences')
@pytest.mark.django_db
def test_save_inline_translation(client, approved_user, language):
    """Test saving inline translation settings."""
    client.force_login(approved_user)

    # Create language preferences first
    lang_prefs = LanguagePreferences.get_or_create_language_preferences(
        approved_user, language
    )

    url = reverse('save_inline_translation')
    data = {
        'language_id': language.google_code,
        'type': 'Translate',
        'parameters': {'model': 'test_model'}
    }

    response = client.post(
        url,
        json.dumps(data),
        content_type='application/json'
    )

    assert response.status_code == 200
    response_data = json.loads(response.content)
    assert response_data['status'] == 'success'
    assert 'inline_translation' in response_data

    # Verify the update
    lang_prefs.refresh_from_db()
    assert lang_prefs.inline_translation_type == 'Translate'
    assert lang_prefs.inline_translation_parameters == {'model': 'test_model'}


@allure.epic('Pages endpoints')
@allure.story('Language Preferences')
@pytest.mark.django_db
class TestLexicalArticleManagement:
    """Test suite for lexical article management endpoints."""

    @pytest.fixture
    def base_url(self):
        return reverse('manage_lexical_article')

    @pytest.fixture
    def article_data(self, language):
        return {
            'action': 'add',
            'language_id': language.google_code,
            'type': 'Translate',
            'title': 'Test Article',
            'parameters': {'model': 'test_model'}
        }

    def test_add_lexical_article(self, client, approved_user, language, base_url, article_data):
        """Test adding a new lexical article."""
        client.force_login(approved_user)

        # Create language preferences first
        LanguagePreferences.get_or_create_language_preferences(approved_user, language)

        response = client.post(
            base_url,
            json.dumps(article_data),
            content_type='application/json'
        )

        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data['status'] == 'success'
        assert 'id' in response_data

        # Verify the article was created
        article = LexicalArticle.objects.get(id=response_data['id'])
        assert article.title == article_data['title']
        assert article.type == article_data['type']
        assert article.parameters == article_data['parameters']

    def test_edit_lexical_article(self, client, approved_user, language, base_url):
        """Test editing an existing lexical article."""
        client.force_login(approved_user)

        # Create language preferences and article first
        lang_prefs = LanguagePreferences.get_or_create_language_preferences(
            approved_user, language
        )
        article = LexicalArticle.objects.create(
            language_preferences=lang_prefs,
            type='Translate',
            title='Original Title',
            parameters={'model': 'old_model'}
        )

        edit_data = {
            'action': 'edit',
            'language_id': language.google_code,
            'id': article.id,
            'type': 'Translate',
            'title': 'Updated Title',
            'parameters': {'model': 'new_model'}
        }

        response = client.post(
            base_url,
            json.dumps(edit_data),
            content_type='application/json'
        )

        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data['status'] == 'success'

        # Verify the update
        article.refresh_from_db()
        assert article.title == 'Updated Title'
        assert article.parameters == {'model': 'new_model'}

    def test_delete_lexical_article(self, client, approved_user, language, base_url):
        """Test deleting a lexical article."""
        client.force_login(approved_user)

        # Create language preferences and article first
        lang_prefs = LanguagePreferences.get_or_create_language_preferences(
            approved_user, language
        )
        article = LexicalArticle.objects.create(
            language_preferences=lang_prefs,
            type='Translate',
            title='To Be Deleted',
            parameters={'model': 'test_model'}
        )

        delete_data = {
            'action': 'delete',
            'language_id': language.google_code,
            'id': article.id
        }

        response = client.post(
            base_url,
            json.dumps(delete_data),
            content_type='application/json'
        )

        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data['status'] == 'success'

        # Verify the deletion
        assert not LexicalArticle.objects.filter(id=article.id).exists()


@allure.epic('Pages endpoints')
@allure.story('Language Preferences')
@pytest.mark.django_db
def test_update_article_order_success(client, approved_user, language):
    """Test updating the order of lexical articles."""
    client.force_login(approved_user)

    # Create language preferences and articles first
    lang_prefs = LanguagePreferences.get_or_create_language_preferences(
        approved_user, language
    )

    # Create three articles to better test reordering
    articles = []
    for i in range(3):
        article = LexicalArticle.objects.create(
            language_preferences=lang_prefs,
            type='Translate',
            title=f'Article {i + 1}',
            parameters={'model': f'model{i + 1}'},
            order=i
        )
        articles.append(article)

    # Move the first article (order 0) to position 1
    url = reverse('update_article_order')
    data = {
        'article_id': articles[0].id,
        'new_index': 1,
        'language_id': language.google_code
    }

    response = client.post(
        url,
        json.dumps(data),
        content_type='application/json'
    )

    assert response.status_code == 200
    response_data = json.loads(response.content)
    assert response_data['status'] == 'success'

    # Refresh all articles from db
    for article in articles:
        article.refresh_from_db()
        print(f"{article.title} -> {article.order}")

    # After moving article[0] to index 1, the order should be:
    # articles[1] -> order 0
    # articles[0] -> order 1
    # articles[2] -> order 2
    assert articles[1].order == DEFAULT_ARTICLES_NUM + 1
    assert articles[0].order == 1
    assert articles[2].order == DEFAULT_ARTICLES_NUM + 2

    # Verify the order in the database matches our expected order
    db_orders = list(
        LexicalArticle.objects.filter(language_preferences=lang_prefs)
        .order_by('order')
        .values_list('title', flat=True)
    )
    assert db_orders[1] == 'Article 1'


@allure.epic('Pages endpoints')
@allure.story('Language Preferences')
@pytest.mark.django_db
def test_update_article_order_to_end(client, approved_user, language):
    """Test moving an article to the end of the list."""
    client.force_login(approved_user)

    # Create language preferences and articles first
    lang_prefs = LanguagePreferences.get_or_create_language_preferences(
        approved_user, language
    )

    # Create three articles
    articles = []
    for i in range(3):
        article = LexicalArticle.objects.create(
            language_preferences=lang_prefs,
            type='Translate',
            title=f'Article {i + 1}',
            parameters={'model': f'model{i + 1}'},
            order=i
        )
        articles.append(article)

    # Move the first article to a high index (should put it at the end)
    url = reverse('update_article_order')
    data = {
        'article_id': articles[0].id,
        'new_index': 999,  # High index should put it at the end
        'language_id': language.google_code
    }

    response = client.post(
        url,
        json.dumps(data),
        content_type='application/json'
    )

    assert response.status_code == 200
    response_data = json.loads(response.content)
    assert response_data['status'] == 'success'

    # Refresh all articles from db
    for article in articles:
        article.refresh_from_db()
        print(f"{article.title} -> {article.order}")

    assert articles[1].order == DEFAULT_ARTICLES_NUM
    assert articles[2].order == DEFAULT_ARTICLES_NUM + 1
    assert articles[0].order == DEFAULT_ARTICLES_NUM + 2

    # Verify the order in the database
    db_orders = list(
        LexicalArticle.objects.filter(language_preferences=lang_prefs)
        .order_by('order')
        .values_list('title', flat=True)
    )
    assert db_orders[DEFAULT_ARTICLES_NUM:] == ['Article 2', 'Article 3', 'Article 1']


@allure.epic('Pages endpoints')
@allure.story('Language Preferences')
@pytest.mark.django_db
def test_update_article_order_nonexistent_article(client, approved_user, language):
    """Test updating the order with a nonexistent article ID."""
    client.force_login(approved_user)

    # Create language preferences
    LanguagePreferences.get_or_create_language_preferences(
        approved_user, language
    )

    url = reverse('update_article_order')
    data = {
        'article_id': 99999,  # Nonexistent ID
        'new_index': 0,
        'language_id': language.google_code
    }

    response = client.post(
        url,
        json.dumps(data),
        content_type='application/json'
    )
    print(response.content)

    assert response.status_code == 400
    response_data = json.loads(response.content)
    assert response_data['status'] == 'error'
    assert 'does not exist' in response_data['message'].lower()

@allure.epic('Pages endpoints')
@allure.story('Language Preferences')
@pytest.mark.django_db
def test_save_inline_translation_invalid_dictionary(client, approved_user, language):
    """Test saving inline translation settings with an invalid dictionary."""
    client.force_login(approved_user)

    # Create language preferences first
    LanguagePreferences.get_or_create_language_preferences(
        approved_user, language
    )

    url = reverse('save_inline_translation')
    data = {
        'language_id': language.google_code,
        'type': 'Dictionary',
        'parameters': {'dictionary': 'invalid_dict'}
    }

    # Mock the translator to raise LanguageNotSupportedException
    with patch('lexiflux.views.language_preferences_views.get_translator') as mock_translator:
        mock_translator.return_value.translate.side_effect = (
            LanguageNotSupportedException('Language not supported')
        )

        response = client.post(
            url,
            json.dumps(data),
            content_type='application/json'
        )

    assert response.status_code == 400
    response_data = json.loads(response.content)
    assert response_data['status'] == 'error'
    assert 'cannot translate' in response_data['message']