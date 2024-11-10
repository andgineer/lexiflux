import pytest
import allure
from lexiflux.forms import CustomUserCreationForm


@allure.epic('Auth')
@allure.story('Create user form')
@pytest.mark.django_db
class TestCustomUserCreationForm:
    @allure.title("Test user creation with valid data")
    def test_form_valid_data(self):
        form = CustomUserCreationForm({
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123'
        })

        assert form.is_valid()

        user = form.save()
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.is_active is True
        assert user.check_password('testpass123')

    @allure.title("Test form validation with mismatched passwords")
    def test_form_passwords_dont_match(self):
        form = CustomUserCreationForm({
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'testpass123',
            'password2': 'differentpass123'
        })

        assert not form.is_valid()
        assert 'password2' in form.errors

    @allure.title("Test form validation with missing email")
    def test_form_missing_email(self):
        form = CustomUserCreationForm({
            'username': 'testuser',
            'password1': 'testpass123',
            'password2': 'testpass123'
        })

        assert not form.is_valid()
        assert 'email' in form.errors

    @allure.title("Test form validation with invalid email format")
    def test_form_invalid_email(self):
        form = CustomUserCreationForm({
            'username': 'testuser',
            'email': 'not_an_email',
            'password1': 'testpass123',
            'password2': 'testpass123'
        })

        assert not form.is_valid()
        assert 'email' in form.errors

    @allure.title("Test form validation with duplicate username")
    def test_form_duplicate_username(self, user):
        form = CustomUserCreationForm({
            'username': user.username,  # Using existing username from user fixture
            'email': 'different@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123'
        })

        assert not form.is_valid()
        assert 'username' in form.errors
