"""URLs for Lexiflux app."""

from django.urls import path, include
from django.contrib.auth.views import LogoutView
from django.contrib import admin

import lexiflux.views.language_preferences_ajax
import lexiflux.views.lexical_views
import lexiflux.views.library_views
import lexiflux.views.reader_views
from lexiflux.views.auth_views import SignUpView, CustomLoginView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", CustomLoginView.as_view(), name="login"),
    path("accounts/logout/", LogoutView.as_view(next_page="login"), name="logout"),
    path("accounts/signup/", SignUpView.as_view(), name="signup"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", lexiflux.views.reader_views.redirect_to_reader, name="redirect_to_reader"),
    path("reader", lexiflux.views.reader_views.reader, name="reader"),
    path("library", lexiflux.views.library_views.library, name="library"),
    path("page", lexiflux.views.reader_views.page, name="page"),
    path("location", lexiflux.views.reader_views.location, name="location"),
    path("history", lexiflux.views.reader_views.add_to_history, name="history"),
    path("translate", lexiflux.views.lexical_views.translate, name="translate"),
    path("book", lexiflux.views.library_views.view_book, name="book"),  # todo: obsolete
    path(
        "language-preferences/",
        lexiflux.views.language_preferences_ajax.language_preferences_editor,
        name="language-preferences",
    ),
    path(
        "api/update-user-language/",
        lexiflux.views.language_preferences_ajax.update_user_language,
        name="api_update_user_language",
    ),
    path(
        "api/get-language-preferences/",
        lexiflux.views.language_preferences_ajax.get_language_preferences,
        name="get_language_preferences",
    ),
    path(
        "api/manage-lexical-article/",
        lexiflux.views.language_preferences_ajax.manage_lexical_article,
        name="manage_lexical_article",
    ),
    path(
        "api/save-inline-translation/",
        lexiflux.views.language_preferences_ajax.save_inline_translation,
        name="save_inline_translation",
    ),
    path(
        "api/save-inline-translation/",
        lexiflux.views.language_preferences_ajax.save_inline_translation,
        name="save_inline_translation",
    ),
    path("api/import-book/", lexiflux.views.library_views.import_book, name="import_book"),
    path("api/books/<int:book_id>/", lexiflux.views.library_views.get_book, name="get_book"),
    path("api/books/<int:book_id>/", lexiflux.views.library_views.update_book, name="update_book"),
    path(
        "api/search-authors/", lexiflux.views.library_views.search_authors, name="search_authors"
    ),
]
