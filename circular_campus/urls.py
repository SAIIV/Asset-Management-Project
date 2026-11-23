"""Top-level URL routes. Each feature owner adds their app's urls here."""

from django.contrib import admin
from django.urls import include, path

from accounts.views import home

urlpatterns = [
    path("", home, name="home"),
    path("accounts/", include("accounts.urls")),
    path("assets/", include("assets.urls")),
    path("inbox/", include("notifications.urls")),
    path("", include("exchange.urls")),
    path("transfers/", include("transfers.urls")),
    path("reports/", include("reports.urls")),
    path("maintenance/", include("assets.maintenance_urls")),




    path("admin/", admin.site.urls),
]
