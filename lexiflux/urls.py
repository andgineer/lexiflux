"""URLs for Lexiflux app."""
from django.urls import path

from . import views

urlpatterns = [
    path("", views.book, name="book"),
    path("page", views.page, name="page"),
    path("viewport", views.viewport, name="viewport"),
    path("translate", views.translate, name="translate"),
    path("profile/", views.profile, name="profile"),
]
