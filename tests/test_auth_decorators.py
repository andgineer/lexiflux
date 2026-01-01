import pytest
import allure
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from unittest.mock import MagicMock, patch
from lexiflux.lexiflux_settings import settings
from lexiflux.auth import get_default_user, smart_login_required

User = get_user_model()


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def mock_view():
    return MagicMock(return_value=HttpResponse())


@allure.epic("User")
@allure.feature("Auth")
class TestAuthDecorators:
    @allure.story("Default User Creation")
    class TestGetDefaultUser:
        @pytest.mark.django_db
        def test_get_default_user_creates_new_user(self):
            """Test that get_default_user creates a new user if it doesn't exist."""
            # Clean up any existing default user
            User.objects.filter(username=settings.lexiflux.default_user_name).delete()

            user = get_default_user()

            assert user.username == settings.lexiflux.default_user_name
            assert User.objects.filter(username=settings.lexiflux.default_user_name).exists()

        @pytest.mark.django_db
        def test_get_default_user_returns_existing_user(self):
            """Test that get_default_user returns existing user if it exists."""
            existing_user = User.objects.create(username=settings.lexiflux.default_user_name)

            user = get_default_user()

            assert user == existing_user
            assert User.objects.filter(username=settings.lexiflux.default_user_name).count() == 1

    @pytest.mark.django_db
    @allure.story("Smart Login Required")
    class TestSmartLoginRequired:
        @pytest.mark.django_db
        def test_skip_auth_anonymous_user(self, request_factory, mock_view):
            """Test decorator with skip_auth=True and anonymous user."""
            request = request_factory.get("/")
            request.user = AnonymousUser()

            with patch("lexiflux.auth.settings.lexiflux.skip_auth", True):
                decorated_view = smart_login_required(mock_view)
                response = decorated_view(request)

                assert isinstance(request.user, User)
                assert request.user.username == settings.lexiflux.default_user_name
                assert mock_view.called
                assert response == mock_view.return_value

        @pytest.mark.django_db
        def test_skip_auth_authenticated_user(self, request_factory, mock_view):
            """Test decorator with skip_auth=True and authenticated user."""
            request = request_factory.get("/")
            request.user = User.objects.create(username="test_user")
            original_user = request.user

            with patch("lexiflux.auth.settings.lexiflux.skip_auth", True):
                decorated_view = smart_login_required(mock_view)
                response = decorated_view(request)

                assert request.user == original_user
                assert mock_view.called
                assert response == mock_view.return_value

        @pytest.mark.django_db
        def test_no_skip_auth_anonymous_user(self, request_factory, mock_view):
            """Test decorator with skip_auth=False and anonymous user."""
            request = request_factory.get("/")
            request.user = AnonymousUser()

            with patch("lexiflux.auth.settings.lexiflux.skip_auth", False):
                decorated_view = smart_login_required(mock_view)
                response = decorated_view(request)

                # Should redirect to login page
                assert response.status_code == 302
                assert "login" in response.url

        @pytest.mark.django_db
        def test_no_skip_auth_authenticated_user(self, request_factory, mock_view):
            """Test decorator with skip_auth=False and authenticated user."""
            request = request_factory.get("/")
            request.user = User.objects.create(username="test_user")

            with patch("lexiflux.auth.settings.lexiflux.skip_auth", False):
                decorated_view = smart_login_required(mock_view)
                response = decorated_view(request)

                assert mock_view.called
                assert response == mock_view.return_value
