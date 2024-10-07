import csv
import datetime
import json
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

import allure
import pytz
from django.utils import timezone
from django.urls import reverse
import pytest
from lexiflux.models import WordsExport, LanguagePreferences, Language


@allure.epic('Pages endpoints')
@allure.story('Words export')
def test_words_export_page_with_translations(client, user_with_translations, translation_history):
    client.force_login(user_with_translations)
    response = client.get(reverse('words-export'))

    assert response.status_code == 200

    context = response.context
    assert 'languages' in context
    assert 'language_groups' in context
    assert 'default_selection' in context
    assert 'last_export_datetime' in context
    assert 'initial_word_count' in context
    assert 'default_deck_name' in context
    assert 'previous_deck_names' in context
    assert 'last_export_format' in context

    languages = json.loads(context['languages'])
    assert len(languages) > 0
    assert any(lang['google_code'] == user_with_translations.default_language_preferences.language.google_code for lang in languages)

    # Additional assertions to verify the content
    assert context['default_selection'] == user_with_translations.default_language_preferences.language.google_code
    assert context['initial_word_count'] > 0
    assert context['default_deck_name']
    assert context['last_export_format']


@allure.epic('Pages endpoints')
@allure.story('Words export')
def test_words_export_page_without_translations(client, approved_user):
    client.force_login(approved_user)
    response = client.get(reverse('words-export'))
    assert response.status_code == 200
    assert response.context['initial_word_count'] == 0


@allure.epic('Pages endpoints')
@allure.story('Words export')
def test_last_export_datetime_language(client, approved_user, language):
    client.force_login(approved_user)
    export_time = timezone.now()
    WordsExport.objects.create(
        user=approved_user,
        language=language,
        word_count=10,
        export_datetime=export_time,
    )
    response = client.get(reverse('last_export_datetime'), {'language': language.google_code})
    assert response.status_code == 200
    data = json.loads(response.content)

    # Parse the datetime strings
    expected_time = export_time.astimezone(pytz.UTC)
    actual_time = datetime.datetime.fromisoformat(data['last_export_datetime']).astimezone(pytz.UTC)

    # Check if the times are within 1 second of each other
    time_difference = abs((expected_time - actual_time).total_seconds())
    assert time_difference < 1, f"Time difference is {time_difference} seconds, which is more than 1 second"


@allure.epic('Pages endpoints')
@allure.story('Words export')
def test_last_export_datetime_language_group(client, approved_user, language_group):
    client.force_login(approved_user)
    export_time = timezone.now()
    WordsExport.objects.create(
        user=approved_user,
        language=language_group.languages.first(),
        word_count=10,
        export_datetime=export_time
    )
    response = client.get(reverse('last_export_datetime'), {'language': str(language_group.id)})
    assert response.status_code == 200
    data = json.loads(response.content)

    # Parse the returned datetime string
    returned_datetime = timezone.datetime.fromisoformat(data['last_export_datetime'])

    # Calculate the difference between the two datetimes
    time_difference = abs(returned_datetime - export_time)

    # Assert that the difference is less than 1 second
    assert time_difference < timedelta(seconds=1), f"Datetime difference ({time_difference}) is too large"


@allure.epic('Pages endpoints')
@allure.story('Words export')
@pytest.mark.parametrize("success", [True, False])
def test_export_words_anki_connect(client, approved_user, language, translation_history, success):
    client.force_login(approved_user)
    data = {
        'language': language.google_code,
        'export_method': 'ankiConnect',
        'min_datetime': (timezone.now() - timedelta(days=1)).isoformat(),
        'deck_name': 'Test Deck'
    }

    with patch('lexiflux.views.words_export.export_words_to_anki_connect') as mock_export:
        if success:
            mock_export.return_value = 1
        else:
            mock_export.side_effect = ValueError("Failed to connect to AnkiConnect")

        response = client.post(reverse('export_words'), json.dumps(data), content_type='application/json')

        assert response.status_code == 200 if success else 500
        response_data = json.loads(response.content)

        if success:
            assert response_data['status'] == 'success'
            assert response_data['exported_words'] == 1

            # Verify that a WordsExport object was created
            assert WordsExport.objects.filter(
                user=approved_user,
                language=language,
                export_format='ankiConnect',
                deck_name='Test Deck'
            ).exists()
        else:
            assert response_data['status'] == 'error'
            assert 'Failed to connect to AnkiConnect' in response_data['error']

        mock_export.assert_called_once()


@allure.epic('Pages endpoints')
@allure.story('Words export')
def test_export_words_anki_file(client, approved_user, language, translation_history):
    client.force_login(approved_user)
    data = {
        'language': language.google_code,
        'export_method': 'ankiFile',
        'min_datetime': (timezone.now() - timedelta(days=1)).isoformat(),
        'deck_name': 'Test Deck'
    }
    with patch('lexiflux.anki.anki_file.export_words_to_anki_file') as mock_export:
        mock_export.return_value = (None, 'test.apkg')
        response = client.post(reverse('export_words'), json.dumps(data), content_type='application/json')
    assert response.status_code == 200
    assert 'attachment; filename="lexiflux_' in response['Content-Disposition']


@allure.epic('Pages endpoints')
@allure.story('Words export')
def test_export_words_csv_file(client, approved_user, language, translation_history):
    client.force_login(approved_user)
    data = {
        'language': language.google_code,
        'export_method': 'csvFile',
        'min_datetime': (timezone.now() - timedelta(days=1)).isoformat(),
        'deck_name': 'Test Deck'
    }
    response = client.post(reverse('export_words'), json.dumps(data), content_type='application/json')

    assert response.status_code == 200
    assert response['Content-Type'] == 'text/csv'
    assert 'Content-Disposition' in response
    assert 'attachment' in response['Content-Disposition']

    # Read the streaming content
    content = b''.join(response.streaming_content).decode('utf-8')

    csv_reader = csv.reader(StringIO(content))
    rows = list(csv_reader)

    # Check CSV structure
    assert len(rows) > 1  # At least header and one data row
    assert rows[0] == ['Term', 'Translation', 'Language', 'Translation Language', 'Sentence']

    # Check if the translation_history data is in the CSV
    found = False
    for row in rows[1:]:
        if row[0] == translation_history.term:
            found = True
            assert row[1] == translation_history.translation
            assert row[2] == translation_history.source_language.name
            assert row[3] == translation_history.target_language.name
            assert "before" in row[4]  # Check if the sentence beginning in the context
            break

    assert found, f"Translation for '{translation_history.term}' not found in CSV"


@allure.epic('Pages endpoints')
@allure.story('Words export')
def test_word_count_language(client, approved_user, language, translation_history):
    client.force_login(approved_user)
    min_datetime = (timezone.now() - timedelta(days=1)).isoformat()
    response = client.get(reverse('word_count'), {'language': language.google_code, 'min_datetime': min_datetime})
    assert response.status_code == 200
    assert json.loads(response.content)['word_count'] == 1


@allure.epic('Pages endpoints')
@allure.story('Words export')
def test_word_count_language_group(client, approved_user, language_group, translation_history):
    client.force_login(approved_user)
    min_datetime = (timezone.now() - timedelta(days=1)).isoformat()
    response = client.get(reverse('word_count'), {'language': str(language_group.id), 'min_datetime': min_datetime})
    assert response.status_code == 200
    assert json.loads(response.content)['word_count'] == 1


@allure.epic('Pages endpoints')
@allure.story('Words export')
def test_export_words_language_group(client, user_with_translations, language_group, translation_history):
    client.force_login(user_with_translations)
    data = {
        'language': str(language_group.id),
        'export_method': 'csvFile',
        'min_datetime': (timezone.now() - timedelta(days=1)).isoformat(),
        'deck_name': 'Test Deck'
    }
    response = client.post(reverse('export_words'), json.dumps(data), content_type='application/json')
    assert response.status_code == 200
    assert response['Content-Type'] == 'text/csv'
    assert 'attachment; filename="lexiflux_' in response['Content-Disposition']


@allure.epic('Pages endpoints')
@allure.story('Words export')
def test_words_export_page_language_preference(client, user_with_translations, language, translation_history):
    client.force_login(user_with_translations)
    response = client.get(reverse('words-export'))
    assert response.status_code == 200

    context = response.context
    assert 'languages' in context
    assert 'language_groups' in context
    assert 'default_selection' in context
    assert 'last_export_datetime' in context
    assert 'initial_word_count' in context
    assert 'default_deck_name' in context
    assert 'previous_deck_names' in context
    assert 'last_export_format' in context

    languages = json.loads(context['languages'])
    assert len(languages) > 0
    assert any(lang['google_code'] == language.google_code for lang in languages)