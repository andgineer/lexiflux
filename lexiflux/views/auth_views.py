"""Views for authentication."""

from typing import Any

from django.contrib.auth import get_user_model, authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import generic

from lexiflux.forms import CustomUserCreationForm


class SignUpView(generic.CreateView):  # type: ignore
    """Sign up view."""

    form_class = CustomUserCreationForm
    success_url = reverse_lazy("login")
    template_name = "signup.html"


UserModel = get_user_model()


class CustomLoginView(LoginView):  # type: ignore
    """Custom login view."""

    template_name = "login.html"

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Handle post request."""
        username = request.POST.get("username")
        password = request.POST.get("password")

        if user := UserModel.objects.get(username=username):
            if user.check_password(password):
                if user.is_approved or user.is_superuser:
                    if user := authenticate(request, username=username, password=password):
                        login(request, user)
                        return redirect(self.get_success_url())
                    error_message = "Internal auth error."
                else:
                    error_message = (
                        "Your account is not approved yet. "
                        "Please wait for an administrator to approve your account."
                    )
            else:
                error_message = (
                    "Please enter a correct username and password! "
                    "Note that both fields may be case-sensitive."
                )
        else:
            error_message = (
                "Please enter a correct username and password! "
                "Note that both fields may be case-sensitive."
            )

        form = AuthenticationForm(initial={"username": username})
        return render(request, self.template_name, {"form": form, "error_message": error_message})
