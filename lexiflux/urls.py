"""URLs for Lexiflux app."""
from django.urls import path

from . import views

urlpatterns = [
    path("", views.reader, name="reader"),
    path("library", views.library, name="library"),
    path("page", views.page, name="page"),
    path("position", views.position, name="position"),
    path("translate", views.translate, name="translate"),
    path("profile", views.profile, name="profile"),
    path("book", views.view_book, name="book"),
]
