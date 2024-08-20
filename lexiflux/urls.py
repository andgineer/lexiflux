"""URLs for Lexiflux app."""

from django.urls import path, include
from django.contrib.auth.views import LogoutView
from django.contrib import admin

import lexiflux.views.language_preferences_ajax
import lexiflux.views.lexical_views
import lexiflux.views.library_views
import lexiflux.views.reader_views
import lexiflux.views.ai_settings_views
from lexiflux.views.auth_views import SignUpView, CustomLoginView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", CustomLoginView.as_view(), name="login"),
    path("accounts/logout/", LogoutView.as_view(next_page="login"), name="logout"),
    path("accounts/signup/", SignUpView.as_view(), name="signup"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", lexiflux.views.reader_views.redirect_to_reader, name="redirect_to_reader"),
    path("reader", lexiflux.views.reader_views.reader, name="reader"),
    path(
        "book/<str:book_code>/image/<path:image_filename>",
        lexiflux.views.reader_views.serve_book_image,
        name="serve_book_image",
    ),
    path("jump", lexiflux.views.reader_views.jump, name="jump"),
    path("jump_back", lexiflux.views.reader_views.jump_back, name="jump_back"),
    path("jump_forward", lexiflux.views.reader_views.jump_forward, name="jump_forward"),
    path("get_jump_status", lexiflux.views.reader_views.get_jump_status, name="get_jump_status"),
    path("page", lexiflux.views.reader_views.page, name="page"),
    path("location", lexiflux.views.reader_views.location, name="location"),
    path("library", lexiflux.views.library_views.library, name="library"),
    path("translate", lexiflux.views.lexical_views.translate, name="translate"),
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
    path(
        "api/update-article-order/",
        lexiflux.views.language_preferences_ajax.update_article_order,
        name="update_article_order",
    ),
    path("api/import-book/", lexiflux.views.library_views.import_book, name="import_book"),
    path(
        "api/books/<int:book_id>/",
        lexiflux.views.library_views.BookDetailView.as_view(),
        name="book_detail",
    ),
    path(
        "api/search-authors/", lexiflux.views.library_views.search_authors, name="search_authors"
    ),
    path("ai-settings/", lexiflux.views.ai_settings_views.ai_settings, name="ai-settings"),
    path(
        "api/ai-settings/",
        lexiflux.views.ai_settings_views.ai_settings_api,
        name="ai_settings_api",
    ),
]
