"""Forms for the users app."""
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):  # type: ignore  # pylint: disable=too-many-ancestors
    """Form for creating a new user."""

    def save(self, commit: bool = True) -> CustomUser:
        user = super().save(commit=False)
        user.is_active = True
        if commit:
            user.save()
        return user  # type: ignore

    class Meta(UserCreationForm.Meta):  # type: ignore
        """Meta class for the form."""

        model = CustomUser
        fields = UserCreationForm.Meta.fields + ("email",)
