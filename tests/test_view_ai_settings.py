import allure
import pytest
import json
from django.urls import reverse
from django.contrib.auth import get_user_model
from pytest_django.asserts import assertTemplateUsed

from lexiflux.models import AIModelConfig, SUPPORTED_CHAT_MODELS


@allure.epic('Pages endpoints')
@allure.story('AI Settings')
@pytest.mark.django_db
def test_ai_settings_view_requires_login(client):
    response = client.get(reverse('ai-settings'))
    assert response.status_code == 302  # Redirects to login page
    assert 'login' in response['Location']  # Verify redirect to login page


@allure.epic('Pages endpoints')
@allure.story('AI Settings')
@pytest.mark.django_db
def test_ai_settings_view_for_regular_user(client, approved_user):
    client.force_login(approved_user)
    response = client.get(reverse('ai-settings'))

    assert response.status_code == 200
    assert 'selected_tab' in response.context
    assert response.context['selected_tab'] == ""
    assertTemplateUsed(response, 'ai-settings.html')


@allure.epic('Pages endpoints')
@allure.story('AI Settings')
@pytest.mark.django_db
def test_ai_settings_view_with_tab_parameter(client, approved_user):
    client.force_login(approved_user)
    response = client.get(reverse('ai-settings') + '?tab=test_tab')

    assert response.status_code == 200
    assert response.context['selected_tab'] == "test_tab"
    assertTemplateUsed(response, 'ai-settings.html')


@allure.epic('Pages endpoints')
@allure.story('AI Settings API')
@pytest.mark.django_db
def test_ai_settings_api_get(client, approved_user):
    client.force_login(approved_user)
    response = client.get(reverse('ai_settings_api'))

    assert response.status_code == 200
    data = json.loads(response.content)
    assert isinstance(data, list)

    # Verify each config has required fields
    for config in data:
        assert 'chat_model' in config
        assert 'caption' in config
        assert 'settings' in config
        assert config['chat_model'] in SUPPORTED_CHAT_MODELS
        # Verify captions match the defined mappings
        if config['chat_model'] == "ChatOpenAI":
            assert config['caption'] == "OpenAI (ChatGPT)"
        elif config['chat_model'] == "ChatMistralAI":
            assert config['caption'] == "Mistral AI"
        elif config['chat_model'] == "ChatAnthropic":
            assert config['caption'] == "Anthropic (Claude)"
        elif config['chat_model'] == "Ollama":
            assert config['caption'] == "Ollama"


@allure.epic('Pages endpoints')
@allure.story('AI Settings API')
@pytest.mark.django_db
def test_ai_settings_api_post_valid_data(client, approved_user):
    client.force_login(approved_user)

    # Create test data for each supported model
    test_data = []
    for model in SUPPORTED_CHAT_MODELS:
        settings = {}
        for key in SUPPORTED_CHAT_MODELS[model]:
            if 'temperature' in key.lower():
                settings[key] = 0.7
            else:  # should be API key
                settings[key] = "https://example.com"

        test_data.append({
            "chat_model": model,
            "settings": settings
        })

    response = client.post(
        reverse('ai_settings_api'),
        data=json.dumps(test_data),
        content_type='application/json'
    )

    print(response.content)
    assert response.status_code == 200
    assert json.loads(response.content) == {"status": "success"}

    # Verify settings were saved
    for model in SUPPORTED_CHAT_MODELS:
        config = AIModelConfig.objects.get(user=approved_user, chat_model=model)
        assert config.settings is not None
        # Verify only valid keys were saved
        assert all(key in SUPPORTED_CHAT_MODELS[model] for key in config.settings.keys())


@allure.epic('Pages endpoints')
@allure.story('AI Settings API')
@pytest.mark.django_db
def test_ai_settings_api_post_invalid_model(client, approved_user):
    client.force_login(approved_user)

    test_data = [{
        "chat_model": "InvalidModel",
        "settings": {"key": "value"}
    }]

    response = client.post(
        reverse('ai_settings_api'),
        data=json.dumps(test_data),
        content_type='application/json'
    )

    assert response.status_code == 400
    assert "Unsupported chat model" in json.loads(response.content)["error"]


@allure.epic('Pages endpoints')
@allure.story('AI Settings API')
@pytest.mark.django_db
def test_ai_settings_api_post_invalid_settings(client, approved_user):
    client.force_login(approved_user)

    # Create test data with invalid settings
    test_data = []
    for model in SUPPORTED_CHAT_MODELS:
        settings = {"invalid_key": "value"}
        for key in SUPPORTED_CHAT_MODELS[model]:
            if 'temperature' in key.lower():
                settings[key] = 0.7
            else:  # should be API key
                settings[key] = "https://example.com"

        test_data.append({
            "chat_model": model,
            "settings": settings
        })

    response = client.post(
        reverse('ai_settings_api'),
        data=json.dumps(test_data),
        content_type='application/json'
    )

    assert response.status_code == 200  # Should still succeed as invalid keys are filtered

    # Verify settings were saved without invalid keys
    for model in SUPPORTED_CHAT_MODELS:
        config = AIModelConfig.objects.get(user=approved_user, chat_model=model)
        assert "invalid_key" not in config.settings
        assert all(key in SUPPORTED_CHAT_MODELS[model] for key in config.settings.keys())


@allure.epic('Pages endpoints')
@allure.story('AI Settings API')
@pytest.mark.django_db
def test_ai_settings_api_invalid_method(client, approved_user):
    client.force_login(approved_user)
    response = client.put(reverse('ai_settings_api'))  # PUT not allowed
    assert response.status_code == 405


@allure.epic('Pages endpoints')
@allure.story('AI Settings API')
@pytest.mark.django_db
def test_ai_settings_api_unauthorized(client):
    response = client.get(reverse('ai_settings_api'))
    assert response.status_code == 302  # Redirects to login page
    assert 'login' in response['Location']


@allure.epic('Pages endpoints')
@allure.story('AI Settings API')
@pytest.mark.django_db
def test_ai_settings_api_get_creates_default_configs(client, approved_user):
    client.force_login(approved_user)

    # Make sure no configs exist initially
    AIModelConfig.objects.all().delete()

    response = client.get(reverse('ai_settings_api'))
    assert response.status_code == 200

    # Verify configs were created for all supported models
    configs = AIModelConfig.objects.filter(user=approved_user)
    assert configs.count() == len(SUPPORTED_CHAT_MODELS)

    # Verify each model has a config
    for model in SUPPORTED_CHAT_MODELS:
        assert configs.filter(chat_model=model).exists()


@allure.epic('Pages endpoints')
@allure.story('AI Settings API')
@pytest.mark.django_db
def test_ai_settings_api_invalid_json(client, approved_user):
    client.force_login(approved_user)

    response = client.post(
        reverse('ai_settings_api'),
        data="invalid json",
        content_type='application/json'
    )

    assert response.status_code == 400
    assert "error" in json.loads(response.content)