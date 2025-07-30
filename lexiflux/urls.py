"""URLs for Lexiflux app."""

from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import include, path

import lexiflux.views.ai_settings_views
import lexiflux.views.calibre_views
import lexiflux.views.import_views
import lexiflux.views.language_preferences_views
import lexiflux.views.lexical_views
import lexiflux.views.library_views
import lexiflux.views.reader_views
import lexiflux.views.search_view
import lexiflux.views.words_export
from lexiflux import settings
from lexiflux.views.auth_views import CustomLoginView, SignUpView
from lexiflux.views.library_views import EditBookModalPartial
from lexiflux.views.user_modal import user_modal

urlpatterns = [
    # admin
    path("admin/", admin.site.urls),
    path("accounts/login/", CustomLoginView.as_view(), name="login"),
    path("accounts/logout/", LogoutView.as_view(next_page="login"), name="logout"),
    path("accounts/signup/", SignUpView.as_view(), name="signup"),
    path("accounts/", include("django.contrib.auth.urls")),
    # library
    path("library", lexiflux.views.library_views.library_page, name="library"),
    # reader
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
    path("link_click", lexiflux.views.reader_views.link_click, name="link_click"),
    path("page", lexiflux.views.reader_views.page, name="page"),
    path("location", lexiflux.views.reader_views.location, name="location"),
    path("search/", lexiflux.views.search_view.search, name="search"),
    path("translate", lexiflux.views.lexical_views.translate, name="translate"),
    # lexical
    path(
        "api/reader-settings/",
        lexiflux.views.reader_views.save_reader_settings,
        name="save_reader_settings",
    ),
    path(
        "language-preferences/",
        lexiflux.views.language_preferences_views.language_preferences_editor,
        name="language-preferences",
    ),
    path(
        "api/update-user-language/",
        lexiflux.views.language_preferences_views.update_user_language,
        name="api_update_user_language",
    ),
    path(
        "api/get-language-preferences/",
        lexiflux.views.language_preferences_views.get_language_preferences,
        name="get_language_preferences",
    ),
    path(
        "api/manage-lexical-article/",
        lexiflux.views.language_preferences_views.manage_lexical_article,
        name="manage_lexical_article",
    ),
    path(
        "api/save-inline-translation/",
        lexiflux.views.language_preferences_views.save_inline_translation,
        name="save_inline_translation",
    ),
    path(
        "api/save-inline-translation/",
        lexiflux.views.language_preferences_views.save_inline_translation,
        name="save_inline_translation",
    ),
    path(
        "api/update-article-order/",
        lexiflux.views.language_preferences_views.update_article_order,
        name="update_article_order",
    ),
    path(
        "api/set-global-language-preferences/",
        lexiflux.views.language_preferences_views.set_global_preferences,
        name="set-global-language-preferences",
    ),
    # ai settings
    path("ai-settings/", lexiflux.views.ai_settings_views.ai_settings, name="ai-settings"),
    path(
        "api/ai-settings/",
        lexiflux.views.ai_settings_views.ai_settings_api,
        name="ai_settings_api",
    ),
    # words export
    path("words-export/", lexiflux.views.words_export.words_export_page, name="words-export"),
    path(
        "api/last-export-datetime/",
        lexiflux.views.words_export.last_export_datetime,
        name="last_export_datetime",
    ),
    path("api/export-words/", lexiflux.views.words_export.export_words, name="export_words"),
    path("api/word-count/", lexiflux.views.words_export.word_count, name="word_count"),
    # user settings
    path("api/user/", user_modal, name="user-modal"),
    # calibre integration
    path(
        "calibre/handshake/",
        lexiflux.views.calibre_views.calibre_handshake,
        name="calibre_handshake",
    ),
    path(
        "calibre/upload/",
        lexiflux.views.calibre_views.calibre_upload_book,
        name="calibre_upload_book",
    ),
    path("calibre/status/", lexiflux.views.calibre_views.calibre_status, name="calibre_status"),
]

# library partials
urlpatterns += [
    path("library/books/", lexiflux.views.library_views.books_list, name="books_list"),
    path("library/import/", lexiflux.views.import_views.import_modal, name="import_modal"),
    path(
        "modals/edit-book/<int:book_id>/",
        EditBookModalPartial.as_view(),
        name="edit_book_modal",
    ),
    path(
        "api/search-authors/",
        lexiflux.views.library_views.search_authors,
        name="search_authors",
    ),
    path("api/import-book/", lexiflux.views.import_views.import_book, name="import_book"),
    path(
        "api/calibre-plugin/",
        lexiflux.views.import_views.download_calibre_plugin,
        name="download_calibre_plugin",
    ),
    path(
        "api/generate-token/",
        lexiflux.views.import_views.generate_api_token,
        name="generate_api_token",
    ),
]

if settings.DEBUGGER_TOOLBAR:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns += debug_toolbar_urls()
