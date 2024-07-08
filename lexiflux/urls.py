"""URLs for Lexiflux app."""

from django.urls import path, include
from django.contrib.auth.views import LogoutView
from django.contrib import admin
from lexiflux import views
from lexiflux.views import SignUpView, CustomLoginView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", CustomLoginView.as_view(), name="login"),
    path("accounts/logout/", LogoutView.as_view(next_page="login"), name="logout"),
    path("accounts/signup/", SignUpView.as_view(), name="signup"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", views.redirect_to_reader, name="redirect_to_reader"),
    path("reader", views.reader, name="reader"),
    path("library", views.library, name="library"),
    path("page", views.page, name="page"),
    path("location", views.location, name="location"),
    path("history", views.add_to_history, name="history"),
    path("translate", views.translate, name="translate"),
    path("book", views.view_book, name="book"),
    path(
        "language-tool-preferences/",
        views.language_tool_preferences,
        name="language-tool-preferences",
    ),
    path(
        "api/get-profile-for-language/",
        views.api_get_profile_for_language,
        name="api_get_profile_for_language",
    ),
    path(
        "api/update-user-language/",
        views.api_update_user_language,
        name="api_update_user_language",
    ),
    path("api/profile/", views.api_profile, name="api_profile"),
    path("manage-lexical-article/", views.manage_lexical_article, name="manage_lexical_article"),
    path(
        "save-inline-translation/", views.save_inline_translation, name="save_inline_translation"
    ),
    path("get-models/", views.get_models, name="get_models"),
    path("update-profile/", views.update_profile, name="update_profile"),
    path(
        "save-inline-translation/", views.save_inline_translation, name="save_inline_translation"
    ),
]
