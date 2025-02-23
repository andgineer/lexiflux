import pytest
import allure
from unittest.mock import patch
from django.contrib.auth import get_user_model
from lexiflux.apps import LexifluxConfig
from lexiflux.lexiflux_settings import AUTOLOGIN_USER_NAME, AUTOLOGIN_USER_PASSWORD

User = get_user_model()


@pytest.fixture
def app_config():
    """Create a properly configured LexifluxConfig instance."""
    app_config = LexifluxConfig.create("lexiflux")
    app_config.path = "."
    return app_config


@allure.epic("User")
@allure.feature("Cloud Environment Validation")
class TestAppConfiguration:
    def test_ready_connects_db_signal(self, app_config):
        """Test that ready() method connects the database connection signal."""
        with patch("django.db.backends.signals.connection_created.connect") as mock_connect:
            app_config.ready()

            mock_connect.assert_called_once_with(
                app_config.on_db_connection, dispatch_uid="validate"
            )

    @pytest.mark.django_db
    def test_app_fails_to_start_with_autologin_user_in_cloud(self, app_config):
        """Test that the app fails to start if auto-login user exists in cloud environment."""
        # Create the auto-login user
        user = User.objects.create_user(
            username=AUTOLOGIN_USER_NAME, password=AUTOLOGIN_USER_PASSWORD
        )

        # Mock cloud environment
        with (
            patch("lexiflux.lexiflux_settings.is_running_in_cloud", return_value=True),
            patch("lexiflux.lexiflux_settings.settings.lexiflux.skip_auth", False),
            pytest.raises(SystemExit) as exc_info,
        ):
            # Simulate database connection
            app_config.on_db_connection(None, None)

        # Verify that the app failed to start
        assert exc_info.type == SystemExit
        assert exc_info.value.code == 1

        # Clean up
        user.delete()

    @pytest.mark.django_db
    def test_app_starts_normally_without_autologin_user(self, app_config):
        """Test that the app starts normally when auto-login user doesn't exist in cloud environment."""
        # Ensure auto-login user doesn't exist
        User.objects.filter(username=AUTOLOGIN_USER_NAME).delete()

        # Mock cloud environment
        with (
            patch("lexiflux.lexiflux_settings.is_running_in_cloud", return_value=True),
            patch("lexiflux.lexiflux_settings.settings.lexiflux.skip_auth", False),
        ):
            # Should not raise any exception
            app_config.on_db_connection(None, None)

    @pytest.mark.django_db
    def test_app_starts_with_autologin_user_in_non_cloud(self, app_config):
        """Test that the app starts when auto-login user exists in non-cloud environment."""
        # Create the auto-login user
        user = User.objects.create_user(
            username=AUTOLOGIN_USER_NAME, password=AUTOLOGIN_USER_PASSWORD
        )

        # Mock non-cloud environment
        with (
            patch("lexiflux.lexiflux_settings.is_running_in_cloud", return_value=False),
            patch("lexiflux.lexiflux_settings.settings.lexiflux.skip_auth", True),
        ):
            # Should not raise any exception
            app_config.on_db_connection(None, None)

        # Clean up
        user.delete()
