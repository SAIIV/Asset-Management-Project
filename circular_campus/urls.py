"""Top-level URL routes. Each feature owner adds their app's urls here."""

from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]
