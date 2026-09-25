import allure
import pytest
from django.urls import reverse
from lexiflux.models import Language, LanguagePreferences


@allure.epic("User")
@allure.feature("User Modal")
@pytest.mark.django_db
def test_user_modal_get(client, approved_user, language):
    client.force_login(approved_user)

    response = client.get(reverse("user-modal"))

    assert response.status_code == 200
    content = response.content.decode()

    # Check that modal contains expected elements
    assert 'id="userModal"' in content
    assert "User Settings" in content
    assert "Select your language" in content
    assert "Save Settings" in content


@allure.epic("User")
@allure.feature("User Modal")
@pytest.mark.django_db
def test_user_modal_update_language(client, approved_user, language):
    client.force_login(approved_user)

    # Get another language (different from the fixture language)
    non_english = language.__class__.objects.exclude(google_code=language.google_code).first()

    # Set initial language for user
    approved_user.language = language
    approved_user.save()

    # Update language via POST
    response = client.post(
        reverse("user-modal"), {"language": non_english.google_code, "update_all_preferences": "on"}
    )

    assert response.status_code == 200
    assert "HX-Refresh" in response.headers

    # Verify user language was updated
    approved_user.refresh_from_db()
    assert approved_user.language == non_english


@allure.epic("User")
@allure.feature("User Modal")
@pytest.mark.django_db
def test_user_modal_update_language_preferences(client, approved_user, language):
    client.force_login(approved_user)

    # Get another language (different from the fixture language)
    non_english = language.__class__.objects.exclude(google_code=language.google_code).first()

    # Set initial language and create language preferences
    approved_user.language = language
    approved_user.save()

    language_pref = LanguagePreferences.objects.create(
        user=approved_user,
        language=non_english,  # Content language
        user_language=language,  # User language
        inline_translation_parameters={"dictionary": "Google"},
    )

    # Update language with update_all_preferences checked
    response = client.post(
        reverse("user-modal"), {"language": non_english.google_code, "update_all_preferences": "on"}
    )

    assert response.status_code == 200

    # Verify language preferences were updated
    language_pref.refresh_from_db()
    assert language_pref.user_language == non_english


@allure.epic("User")
@allure.feature("User Modal")
@pytest.mark.django_db
def test_user_modal_update_without_affecting_preferences(client, approved_user, language):
    client.force_login(approved_user)

    # Get another language (different from the fixture language)
    non_english = language.__class__.objects.exclude(google_code=language.google_code).first()

    # Set initial language and create language preferences
    approved_user.language = language
    approved_user.save()

    language_pref = LanguagePreferences.objects.create(
        user=approved_user,
        language=non_english,  # Content language
        user_language=language,  # User language
        inline_translation_parameters={"dictionary": "Google"},
    )

    # Update language without update_all_preferences
    response = client.post(reverse("user-modal"), {"language": non_english.google_code})

    assert response.status_code == 200

    # Verify user language was updated but language preferences weren't
    approved_user.refresh_from_db()
    language_pref.refresh_from_db()
    assert approved_user.language == non_english
    assert language_pref.user_language == language  # Unchanged


@allure.epic("User")
@allure.feature("User Modal")
@pytest.mark.django_db
def test_first_time_user_language_selection(client, approved_user, language):
    client.force_login(approved_user)

    # Ensure user has no language set
    approved_user.language = None
    approved_user.save()

    # Get a language from the fixture
    english = language

    # Instead of creating a new language preference with null user_language
    # (which the model doesn't allow), we'll rely on the signal that
    # creates preferences for users or use a mock

    # Get modal first to verify welcome message
    response = client.get(reverse("user-modal"))
    content = response.content.decode()
    assert "Welcome to LexiFlux!" in content

    # Set language for first time
    response = client.post(reverse("user-modal"), {"language": english.google_code})

    assert response.status_code == 200

    # Verify the user language was updated
    approved_user.refresh_from_db()
    assert approved_user.language == english

    # Verify language preferences were updated
    # Find all language preferences for this user and check their user_language
    language_prefs = LanguagePreferences.objects.filter(user=approved_user)
    for pref in language_prefs:
        assert pref.user_language == english


def _serbian_titles(user):
    serbian = LanguagePreferences.objects.get(user=user, language__google_code="sr")
    return [article.title for article in serbian.get_lexical_articles()]


@allure.epic("User")
@allure.feature("User Modal")
@pytest.mark.django_db
@pytest.mark.parametrize(
    "language, lingea",
    [("ru", ["lingea"]), ("en", ["lingea"]), ("ka", [])],
)
def test_first_language_choice_of_a_lingea_language_adds_lingea_to_serbian(
    client, user, language, lingea
):
    client.force_login(user)
    assert user.language is None

    response = client.post(reverse("user-modal"), {"language": language})

    assert response.status_code == 200
    assert _serbian_titles(user) == ["Article", "In depth", "Sentence", "glosbe", *lingea]


@allure.epic("User")
@allure.feature("User Modal")
@pytest.mark.django_db
def test_later_language_change_adds_no_articles(client, approved_user):
    approved_user.language = Language.objects.get(google_code="ka")
    approved_user.save()
    client.force_login(approved_user)

    client.post(reverse("user-modal"), {"language": "ru", "update_all_preferences": "on"})

    assert _serbian_titles(approved_user) == ["Article", "In depth", "Sentence", "glosbe"]


@allure.epic("User")
@allure.feature("User Modal")
@pytest.mark.django_db
def test_user_modal_invalid_language(client, approved_user, language):
    client.force_login(approved_user)

    # Try to update with invalid language code
    response = client.post(reverse("user-modal"), {"language": "invalid_code"})

    # Should return 400 Bad Request
    assert response.status_code == 400


@allure.epic("User")
@allure.feature("User Modal")
@pytest.mark.django_db
def test_user_modal_missing_language(client, approved_user, language):
    client.force_login(approved_user)

    # Try to update without providing language
    response = client.post(reverse("user-modal"), {})

    # Should return 400 Bad Request
    assert response.status_code == 400
