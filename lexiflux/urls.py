"""URLs for LexiFlux app."""
from django.urls import path

from . import views

urlpatterns = [
    path("", views.book, name="book"),
]
