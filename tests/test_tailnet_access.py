import importlib

import allure
import pytest
from django.test import Client, override_settings
from django.urls import reverse

from lexiflux.environments import local

TAILNET_HOST = "macbook.tail1e48d.ts.net"
TAILNET_ORIGIN = f"https://{TAILNET_HOST}"
# What `tailscale serve` adds when proxying an HTTPS request.
TAILSCALE_SERVE_HEADERS = {
    "HTTP_HOST": TAILNET_HOST,
    "HTTP_X_FORWARDED_PROTO": "https",
    "HTTP_X_FORWARDED_HOST": TAILNET_HOST,
    "HTTP_X_FORWARDED_FOR": "100.101.102.103",
}

local_hosts = override_settings(ALLOWED_HOSTS=local._default_allowed_hosts)


@allure.epic("Settings")
@allure.feature("Tailnet access")
class TestTailnetAccess:
    @local_hosts
    @pytest.mark.django_db
    def test_tailnet_host_is_accepted_and_secure(self):
        response = Client().get(reverse("login"), **TAILSCALE_SERVE_HEADERS)

        assert response.status_code == 200
        assert response.wsgi_request.is_secure()
        assert response.wsgi_request.build_absolute_uri("/").startswith(TAILNET_ORIGIN)

    @local_hosts
    @pytest.mark.django_db
    def test_unrelated_host_is_rejected(self):
        response = Client().get(reverse("login"), HTTP_HOST="evil.example.com")

        assert response.status_code == 400

    @local_hosts
    @pytest.mark.django_db
    def test_post_from_tailnet_origin_with_csrf_token_passes(self):
        client = Client(enforce_csrf_checks=True)
        client.get(reverse("login"), **TAILSCALE_SERVE_HEADERS)
        token = client.cookies["csrftoken"].value

        response = client.post(
            reverse("login"),
            {"username": "nobody", "password": "wrong", "csrfmiddlewaretoken": token},
            HTTP_ORIGIN=TAILNET_ORIGIN,
            HTTP_REFERER=f"{TAILNET_ORIGIN}/accounts/login/",
            **TAILSCALE_SERVE_HEADERS,
        )

        assert response.status_code == 200

    @local_hosts
    @pytest.mark.django_db
    def test_post_from_foreign_origin_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.get(reverse("login"), **TAILSCALE_SERVE_HEADERS)
        token = client.cookies["csrftoken"].value

        response = client.post(
            reverse("login"),
            {"username": "nobody", "password": "wrong", "csrfmiddlewaretoken": token},
            HTTP_ORIGIN="https://evil.example.com",
            **TAILSCALE_SERVE_HEADERS,
        )

        assert response.status_code == 403

    @local_hosts
    @pytest.mark.django_db
    def test_forwarded_proto_from_non_loopback_peer_is_ignored(self):
        response = Client().get(
            reverse("login"),
            REMOTE_ADDR="192.168.1.20",
            **TAILSCALE_SERVE_HEADERS,
        )

        assert response.status_code == 200
        assert not response.wsgi_request.is_secure()

    def test_allowed_hosts_env_override_replaces_defaults(self, monkeypatch):
        monkeypatch.setenv("LEXIFLUX_ALLOWED_HOSTS", "example.org, other.org")
        try:
            assert importlib.reload(local).ALLOWED_HOSTS == ["example.org", "other.org"]
        finally:
            monkeypatch.delenv("LEXIFLUX_ALLOWED_HOSTS")
            importlib.reload(local)

        assert ".ts.net" in local.ALLOWED_HOSTS
