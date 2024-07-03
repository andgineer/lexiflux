"""URLs for Lexiflux app."""

from django.urls import path

from lexiflux import views

urlpatterns = [
    path("", views.redirect_to_reader, name="redirect_to_reader"),
    path("reader", views.reader, name="reader"),
    path("library", views.library, name="library"),
    path("page", views.page, name="page"),
    path("location", views.location, name="location"),
    path("history", views.add_to_history, name="history"),
    path("translate", views.translate, name="translate"),
    path("book", views.view_book, name="book"),
    path("profile/", views.profile, name="profile"),
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
