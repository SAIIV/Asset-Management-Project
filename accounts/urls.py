from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.SignInView.as_view(), name="login"),
    path("logout/", views.SignOutView.as_view(), name="logout"),
]
