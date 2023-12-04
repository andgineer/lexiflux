"""URLs for Lexiflux app."""
from django.contrib import admin
from django.urls import include, path

from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("signup/", views.SignUpView.as_view(), name="signup"),
    path("", views.book, name="book"),
    path("page", views.page, name="page"),
    path("viewport", views.viewport, name="viewport"),
    path("translate", views.translate, name="translate"),
    path("profile/", views.profile, name="profile"),
]
