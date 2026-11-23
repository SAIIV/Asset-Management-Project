from django.urls import path

from . import assistant_views as views

app_name = "assistant"

urlpatterns = [
    path("", views.page, name="page"),
    path("new/", views.new_chat, name="new"),
    path("c/<int:pk>/", views.chat_page, name="chat"),
    path("c/<int:pk>/delete/", views.delete_chat, name="delete"),
    path("send/", views.send_view, name="send"),
    path("latest/", views.latest_json, name="latest"),
    path("m/<int:pk>/rate/", views.rate_view, name="rate"),
    path("m/<int:pk>/photo/", views.photo, name="photo"),
    path("memory/forget/", views.forget_view, name="forget"),
]
