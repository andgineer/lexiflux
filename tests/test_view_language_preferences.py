import json
from unittest.mock import patch

import allure
import pytest
from deep_translator.exceptions import LanguageNotSupportedException
from django.urls import reverse

from lexiflux.language_preferences_default import DEFAULT_LEXICAL_ARTICLES
from lexiflux.models import LanguagePreferences, LexicalArticle


DEFAULT_ARTICLES_NUM = len(DEFAULT_LEXICAL_ARTICLES)  # created in migrations


@allure.epic("Pages endpoints")
@allure.story("Language Preferences")
@pytest.mark.django_db
def test_language_preferences_unauthorized_access(client):
    """Test that unauthorized users are redirected to login."""
    response = client.get(reverse("language-preferences"))
    assert response.status_code == 302
    assert response.url.startswith("/accounts/login")


@allure.epic("Pages endpoints")
@allure.story("Language Preferences")
@pytest.mark.django_db
def test_language_preferences_editor_view(client, approved_user):
    """Test the main language preferences editor view."""
    client.force_login(approved_user)
    response = client.get(reverse("language-preferences"))

    assert response.status_code == 200
    assert "language-preferences.html" in [t.name for t in response.templates]

    context = response.context
    assert context["user"] == approved_user
    assert "all_languages" in context
    assert "articles" in context
    assert "inline_translation" in context
    assert "lexical_article_types" in context
    assert "ai_models" in context
    assert "translators" in context


@allure.epic("Pages endpoints")
@allure.story("Language Preferences")
@pytest.mark.django_db
def test_get_language_preferences(client, approved_user, language):
    """Test getting language preferences for a specific language."""
    client.force_login(approved_user)

    url = reverse("get_language_preferences")
    data = {"language_id": language.google_code}

    response = client.post(url, json.dumps(data), content_type="application/json")

    assert response.status_code == 200
    response_data = json.loads(response.content)
    assert response_data["status"] == "success"
    assert "language_preferences_id" in response_data
    assert "articles" in response_data
    assert "inline_translation" in response_data
    assert "all_languages" in response_data


@allure.epic("Pages endpoints")
@allure.story("Language Preferences")
@pytest.mark.django_db
def test_update_user_language(client, approved_user, language):
    """Test updating user language preferences."""
    client.force_login(approved_user)

    # Create language preferences first
    lang_prefs = LanguagePreferences.get_or_create_language_preferences(approved_user, language)

    url = reverse("api_update_user_language")
    data = {
        "language_id": language.google_code,
        "language_preferences_language_id": language.google_code,
    }

    response = client.post(url, json.dumps(data), content_type="application/json")

    assert response.status_code == 200
    response_data = json.loads(response.content)
    assert response_data["status"] == "success"

    # Verify the update
    lang_prefs.refresh_from_db()
    assert lang_prefs.user_language == language


@allure.epic("Pages endpoints")
@allure.story("Language Preferences")
@pytest.mark.django_db
def test_save_inline_translation(client, approved_user, language):
    """Test saving inline translation settings."""
    client.force_login(approved_user)

    # Create language preferences first
    lang_prefs = LanguagePreferences.get_or_create_language_preferences(approved_user, language)

    url = reverse("save_inline_translation")
    data = {
        "language_id": language.google_code,
        "type": "Translate",
        "parameters": {"model": "gpt"},
    }

    response = client.post(url, json.dumps(data), content_type="application/json")

    assert response.status_code == 200
    response_data = json.loads(response.content)
    assert response_data["status"] == "success"
    assert "inline_translation" in response_data

    # Verify the update
    lang_prefs.refresh_from_db()
    assert lang_prefs.inline_translation_type == "Translate"
    assert lang_prefs.inline_translation_parameters == {"model": "gpt"}


@allure.epic("Pages endpoints")
@allure.story("Language Preferences")
@pytest.mark.django_db
class TestLexicalArticleManagement:
    """Test suite for lexical article management endpoints."""

    @pytest.fixture
    def lang_prefs_url(self):
        return reverse("manage_lexical_article")

    @pytest.fixture
    def article_data(self, language):
        return {
            "action": "add",
            "language_id": language.google_code,
            "type": "Translate",
            "title": "Test Article",
            "parameters": {"model": "gpt"},
        }

    def test_add_lexical_article(
        self, client, approved_user, language, lang_prefs_url, article_data
    ):
        """Test adding a new lexical article."""
        client.force_login(approved_user)

        # Create language preferences first
        LanguagePreferences.get_or_create_language_preferences(approved_user, language)

        response = client.post(
            lang_prefs_url, json.dumps(article_data), content_type="application/json"
        )

        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data["status"] == "success"
        assert "id" in response_data

        # Verify the article was created
        article = LexicalArticle.objects.get(id=response_data["id"])
        assert article.title == article_data["title"]
        assert article.type == article_data["type"]
        assert article.parameters == article_data["parameters"]

    def test_edit_lexical_article(self, client, approved_user, language, lang_prefs_url):
        """Test editing an existing lexical article."""
        client.force_login(approved_user)

        # Create language preferences and article first
        lang_prefs = LanguagePreferences.get_or_create_language_preferences(approved_user, language)
        article = LexicalArticle.objects.create(
            language_preferences=lang_prefs,
            type="Translate",
            title="Original Title",
            parameters={"model": "gpt-fast"},
        )

        edit_data = {
            "action": "edit",
            "language_id": language.google_code,
            "id": article.id,
            "type": "Translate",
            "title": "Updated Title",
            "parameters": {"model": "opus"},
        }

        response = client.post(
            lang_prefs_url, json.dumps(edit_data), content_type="application/json"
        )

        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data["status"] == "success"

        # Verify the update
        article.refresh_from_db()
        assert article.title == "Updated Title"
        assert article.parameters == {"model": "opus"}

    def test_delete_lexical_article(self, client, approved_user, language, lang_prefs_url):
        """Test deleting a lexical article."""
        client.force_login(approved_user)

        # Create language preferences and article first
        lang_prefs = LanguagePreferences.get_or_create_language_preferences(approved_user, language)
        article = LexicalArticle.objects.create(
            language_preferences=lang_prefs,
            type="Translate",
            title="To Be Deleted",
            parameters={"model": "gpt"},
        )

        delete_data = {"action": "delete", "language_id": language.google_code, "id": article.id}

        response = client.post(
            lang_prefs_url, json.dumps(delete_data), content_type="application/json"
        )

        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data["status"] == "success"

        # Verify the deletion
        assert not LexicalArticle.objects.filter(id=article.id).exists()


@allure.epic("Pages endpoints")
@allure.story("Language Preferences")
@pytest.mark.django_db
def test_update_article_order_success(client, approved_user, language):
    """Test updating the order of lexical articles."""
    client.force_login(approved_user)

    # Create language preferences and articles first
    lang_prefs = LanguagePreferences.get_or_create_language_preferences(approved_user, language)

    # Create three articles to better test reordering
    articles = []
    for i in range(3):
        article = LexicalArticle.objects.create(
            language_preferences=lang_prefs,
            type="Translate",
            title=f"Article {i + 1}",
            parameters={"model": ["pool", "gpt", "opus"][i]},
            order=DEFAULT_ARTICLES_NUM + i,
        )
        articles.append(article)

    # Move the first article (order 0) to position 1
    url = reverse("update_article_order")
    data = {"article_id": articles[0].id, "new_index": 1, "language_id": language.google_code}

    response = client.post(url, json.dumps(data), content_type="application/json")

    assert response.status_code == 200
    response_data = json.loads(response.content)
    assert response_data["status"] == "success"

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
        .order_by("order")
        .values_list("title", flat=True)
    )
    assert db_orders[1] == "Article 1"


@allure.epic("Pages endpoints")
@allure.story("Language Preferences")
@pytest.mark.django_db
def test_update_article_order_to_end(client, approved_user, language):
    """Test moving an article to the end of the list."""
    client.force_login(approved_user)

    # Create language preferences and articles first
    lang_prefs = LanguagePreferences.get_or_create_language_preferences(approved_user, language)

    # Create three articles
    articles = []
    for i in range(3):
        article = LexicalArticle.objects.create(
            language_preferences=lang_prefs,
            type="Translate",
            title=f"Article {i + 1}",
            parameters={"model": ["pool", "gpt", "opus"][i]},
            order=DEFAULT_ARTICLES_NUM + i,
        )
        articles.append(article)

    # Move the first article to a high index (should put it at the end)
    url = reverse("update_article_order")
    data = {
        "article_id": articles[0].id,
        "new_index": 999,  # High index should put it at the end
        "language_id": language.google_code,
    }

    response = client.post(url, json.dumps(data), content_type="application/json")

    assert response.status_code == 200
    response_data = json.loads(response.content)
    assert response_data["status"] == "success"

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
        .order_by("order")
        .values_list("title", flat=True)
    )
    assert db_orders[DEFAULT_ARTICLES_NUM:] == ["Article 2", "Article 3", "Article 1"]


@allure.epic("Pages endpoints")
@allure.story("Language Preferences")
@pytest.mark.django_db
def test_update_article_order_nonexistent_article(client, approved_user, language):
    """Test updating the order with a nonexistent article ID."""
    client.force_login(approved_user)

    # Create language preferences
    LanguagePreferences.get_or_create_language_preferences(approved_user, language)

    url = reverse("update_article_order")
    data = {
        "article_id": 99999,  # Nonexistent ID
        "new_index": 0,
        "language_id": language.google_code,
    }

    response = client.post(url, json.dumps(data), content_type="application/json")
    print(response.content)

    assert response.status_code == 400
    response_data = json.loads(response.content)
    assert response_data["status"] == "error"
    assert "does not exist" in response_data["message"].lower()


@allure.epic("Pages endpoints")
@allure.story("Language Preferences")
@pytest.mark.django_db
def test_save_inline_translation_invalid_dictionary(client, approved_user, language):
    """Test saving inline translation settings with an invalid dictionary."""
    client.force_login(approved_user)

    # Create language preferences first
    LanguagePreferences.get_or_create_language_preferences(approved_user, language)

    url = reverse("save_inline_translation")
    data = {
        "language_id": language.google_code,
        "type": "Dictionary",
        "parameters": {"dictionary": "invalid_dict"},
    }

    # Mock the translator to raise LanguageNotSupportedException
    with patch("lexiflux.views.language_preferences_views.get_translator") as mock_translator:
        mock_translator.return_value.translate.side_effect = LanguageNotSupportedException(
            "Language not supported"
        )

        response = client.post(url, json.dumps(data), content_type="application/json")

    assert response.status_code == 400
    response_data = json.loads(response.content)
    assert response_data["status"] == "error"
    assert "cannot translate" in response_data["message"]


@allure.epic("Pages endpoints")
@allure.story("Language Preferences")
@pytest.mark.django_db
def test_editor_offers_the_models_with_their_knobs(client, approved_user):
    client.force_login(approved_user)

    response = client.get(reverse("language-preferences"))

    models = {model["key"]: model for model in json.loads(response.context["ai_models"])}
    assert list(models) == ["pool", "gpt", "gpt-fast", "opus"]
    assert models["pool"]["efforts"] == [] and models["pool"]["tiers"] == []
    assert models["pool"]["defaults"] == {}
    assert models["gpt"]["efforts"] == ["none", "low", "medium", "high"]
    assert models["gpt"]["tiers"] == ["priority", "standard"]
    assert models["gpt"]["defaults"] == {"effort": "none", "tier": "priority"}
    assert models["gpt-fast"]["defaults"] == {"effort": "low", "tier": "priority"}
    assert models["opus"]["tiers"] == []
    assert models["opus"]["defaults"] == {"effort": "low"}
    assert response.context["default_ai_model"] == "gpt"

    page = response.content.decode()
    assert "defaultAiModel: 'gpt'" in page
    assert 'id="effort-select"' in page
    assert 'id="tier-select"' in page
    assert "about 3× faster (measured on Sol)" in page
    assert "[HIGHLIGHT]" not in page
    assert "{sentence}" in page


@allure.epic("Pages endpoints")
@allure.story("Language Preferences")
@pytest.mark.django_db
def test_editor_hides_a_model_the_catalog_dropped(client, approved_user):
    client.force_login(approved_user)

    with patch(
        "lexiflux.language.ai_models._catalog_providers",
        return_value={"gpt": "openai", "gpt-fast": "openai"},
    ):
        response = client.get(reverse("language-preferences"))

    keys = [model["key"] for model in json.loads(response.context["ai_models"])]
    assert keys == ["pool", "gpt", "gpt-fast"]


@allure.epic("Pages endpoints")
@allure.story("Language Preferences")
@pytest.mark.django_db
class TestArticleKnobs:
    def _post(self, client, data):
        return client.post(
            reverse("manage_lexical_article"), json.dumps(data), content_type="application/json"
        )

    def _add(self, client, language, parameters, article_type="In depth"):
        return self._post(
            client,
            {
                "action": "add",
                "language_id": language.google_code,
                "type": article_type,
                "title": "Knobs",
                "parameters": parameters,
            },
        )

    @pytest.fixture(autouse=True)
    def logged_in(self, client, approved_user, language):
        client.force_login(approved_user)
        return LanguagePreferences.get_or_create_language_preferences(approved_user, language)

    def test_knobs_are_saved_in_the_parameters(self, client, language):
        response = self._add(
            client, language, {"model": "gpt", "effort": "high", "tier": "standard"}
        )

        assert response.status_code == 200
        article = LexicalArticle.objects.get(id=response.json()["id"])
        assert article.parameters == {"model": "gpt", "effort": "high", "tier": "standard"}

    def test_model_default_knobs_and_foreign_parameters_are_dropped(self, client, language):
        response = self._add(
            client,
            language,
            {"model": "gpt-fast", "effort": "", "tier": "", "url": "https://x", "prompt": "p"},
        )

        assert response.status_code == 200
        article = LexicalArticle.objects.get(id=response.json()["id"])
        assert article.parameters == {"model": "gpt-fast"}

    @pytest.mark.parametrize(
        "parameters",
        [
            {"model": "opus", "tier": "priority"},
            {"model": "pool", "effort": "low"},
            {"model": "gpt", "effort": "extreme"},
            {"model": "claude-sonnet-4-0"},
        ],
    )
    def test_invalid_knobs_are_rejected_on_add(self, client, language, parameters):
        response = self._add(client, language, parameters)

        assert response.status_code == 400
        assert response.json()["status"] == "error"
        assert not LexicalArticle.objects.filter(title="Knobs").exists()

    def test_invalid_knob_is_rejected_on_edit(self, client, language, logged_in):
        article = LexicalArticle.objects.create(
            language_preferences=logged_in,
            type="Translate",
            title="Edit me",
            parameters={"model": "gpt", "effort": "none"},
            order=10,
        )

        response = self._post(
            client,
            {
                "action": "edit",
                "language_id": language.google_code,
                "id": article.id,
                "type": "Translate",
                "title": "Edit me",
                "parameters": {"model": "opus", "tier": "priority"},
            },
        )

        assert response.status_code == 400
        article.refresh_from_db()
        assert article.parameters == {"model": "gpt", "effort": "none"}

    def test_edit_changes_model_and_knobs(self, client, language, logged_in):
        article = LexicalArticle.objects.create(
            language_preferences=logged_in,
            type="Translate",
            title="Edit me",
            parameters={"model": "gpt", "effort": "none", "tier": "priority"},
            order=10,
        )

        response = self._post(
            client,
            {
                "action": "edit",
                "language_id": language.google_code,
                "id": article.id,
                "type": "Translate",
                "title": "Edit me",
                "parameters": {"model": "opus", "effort": "low", "tier": ""},
            },
        )

        assert response.status_code == 200
        article.refresh_from_db()
        assert article.parameters == {"model": "opus", "effort": "low"}

    def test_inline_translation_keeps_valid_knobs_and_rejects_invalid(
        self, client, language, logged_in
    ):
        url = reverse("save_inline_translation")
        valid = {
            "language_id": language.google_code,
            "type": "Translate",
            "parameters": {"model": "gpt-fast", "effort": "low", "tier": "priority"},
        }
        invalid = {**valid, "parameters": {"model": "opus", "tier": "priority"}}

        assert (
            client.post(url, json.dumps(valid), content_type="application/json").status_code == 200
        )
        assert (
            client.post(url, json.dumps(invalid), content_type="application/json").status_code
            == 400
        )

        logged_in.refresh_from_db()
        assert logged_in.inline_translation_parameters == {
            "model": "gpt-fast",
            "effort": "low",
            "tier": "priority",
        }
