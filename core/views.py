from django.urls import reverse_lazy
from django.views import generic
from core.forms import CustomUserCreationForm
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.shortcuts import redirect
from django.shortcuts import render
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model, login
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.shortcuts import render, redirect


class SignUpView(generic.CreateView):  # type: ignore
    """Sign up view."""

    form_class = CustomUserCreationForm
    success_url = reverse_lazy("login")
    template_name = "signup.html"


UserModel = get_user_model()


class CustomLoginView(LoginView):
    template_name = "login.html"

    def post(self, request, *args, **kwargs):
        username = request.POST.get('username')
        password = request.POST.get('password')

        print(username, password)

        user = UserModel.objects.get(username=username)
        if user:
            print(user.is_approved, user.is_superuser)
            if user.check_password(password):
                print(user.is_approved, user.is_superuser)
                if user.is_approved or user.is_superuser:
                    print("approved")
                    user = authenticate(request, username=username, password=password)
                    if user:
                        login(request, user)
                        return redirect(self.get_success_url())
                    else:
                        error_message = "Internal auth error."
                else:
                    print("not approved")
                    error_message = "Your account is not approved yet. Please wait for an administrator to approve your account."
            else:
                print("wrong password")
                error_message = "Please enter a correct username and password! Note that both fields may be case-sensitive."
        else:
            error_message = "Please enter a correct username and password! Note that both fields may be case-sensitive."

        form = AuthenticationForm(initial={'username': username})
        return render(request, self.template_name, {
            'form': form,
            'error_message': error_message
        })




