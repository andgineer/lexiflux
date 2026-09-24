import allure
import pytest
from django.urls import NoReverseMatch, reverse


@allure.epic("Pages endpoints")
@allure.feature("AI Settings removed")
@pytest.mark.django_db
@pytest.mark.parametrize("url", ["/ai-settings/", "/api/ai-settings/"])
def test_ai_settings_url_is_gone(client, approved_user, url):
    client.force_login(approved_user)
    assert client.get(url).status_code == 404


@allure.epic("Pages endpoints")
@allure.feature("AI Settings removed")
def test_ai_settings_route_names_are_gone():
    for name in ("ai-settings", "ai_settings_api"):
        with pytest.raises(NoReverseMatch):
            reverse(name)


@allure.epic("Pages endpoints")
@allure.feature("AI Settings removed")
@pytest.mark.django_db
def test_menu_has_no_ai_settings_link(client, approved_user):
    client.force_login(approved_user)
    response = client.get(reverse("library"))
    assert response.status_code == 200
    content = response.content.decode()
    assert "AI Connections" not in content
    assert "ai-settings" not in content
