from django.urls import path

from . import assistant_views as views

app_name = "assistant"

urlpatterns = [
    path("", views.page, name="page"),
    path("<int:record_id>/rate/", views.rate, name="rate"),
]
