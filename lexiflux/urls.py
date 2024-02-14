"""URLs for Lexiflux app."""
from django.urls import path

from . import views

urlpatterns = [
    path("", views.redirect_to_reader, name="redirect_to_reader"),
    path("reader", views.reader, name="reader"),
    path("reader/<str:book_code>/", views.reader, name="read_the_book"),
    path("library", views.library, name="library"),
    path("page", views.page, name="page"),
    path("location", views.location, name="location"),
    path("translate", views.translate, name="translate"),
    path("profile", views.profile, name="profile"),
    path("book", views.view_book, name="book"),
]
