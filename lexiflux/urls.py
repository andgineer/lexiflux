"""URLs for Lexiflux app."""
from django.urls import path

from . import views

urlpatterns = [
    path("", views.book, name="book"),
    path("next-page", views.next_page, name="next-page"),
    path("previous-page", views.previous_page, name="previous-page"),
    path("word", views.word_click, name="word"),
]
