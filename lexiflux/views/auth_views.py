"""Views for authentication."""

from typing import Any

from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.core.exceptions import ObjectDoesNotExist
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

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:  # noqa: ARG002
        """Handle post request."""
        username = request.POST.get("username")
        password = request.POST.get("password")
        try:
            user = UserModel.objects.get(username=username)
            if user.is_approved or user.is_superuser:
                if user := authenticate(request, username=username, password=password):
                    login(request, user)
                    return redirect(self.get_success_url())
                error_message = "Invalid username or password."
            else:
                error_message = (
                    "Your account is not approved yet. "
                    "Please wait for an administrator to approve your account."
                )
        except ObjectDoesNotExist:
            error_message = "Invalid username or password."

        form = AuthenticationForm(initial={"username": username})
        return render(request, self.template_name, {"form": form, "error_message": error_message})
