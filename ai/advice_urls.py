from django.urls import path

from . import advice_views as views

app_name = "advice"

urlpatterns = [
    path("assets/<int:pk>/", views.ask, name="ask"),
    path("assets/<int:pk>/<int:record_id>/answer/", views.answer, name="answer"),
]
