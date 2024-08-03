import allure
import pytest
from django.core.management import CommandError
from lexiflux.utils import validate_log_level
import logging


@allure.epic('Book import')
@allure.feature('Logging')
@pytest.mark.parametrize("level_name,expected", [
    ("DEBUG", logging.DEBUG),
    ("INFO", logging.INFO),
    ("WARNING", logging.WARNING),
    ("ERROR", logging.ERROR),
    ("CRITICAL", logging.CRITICAL),
])
def test_validate_log_level_valid(level_name, expected):
    """Test validate_log_level with valid log levels."""
    assert validate_log_level(level_name) == expected


@allure.epic('Book import')
@allure.feature('Logging')
@pytest.mark.parametrize("level_name", [
    "INVALID",  # Completely invalid
    "debugg",   # Misspelled
    "infoo",    # Misspelled
])
def test_validate_log_level_invalid(level_name):
    """Test validate_log_level with invalid log levels."""
    with pytest.raises(CommandError) as e_info:
        validate_log_level(level_name)
    assert f"Invalid log level '{level_name}'." in str(e_info.value)

