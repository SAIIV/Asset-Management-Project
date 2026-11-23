from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.SignInView.as_view(), name="login"),
    path("logout/", views.SignOutView.as_view(), name="logout"),
    path("me/", views.account, name="account"),
    path("me/password/", views.change_password, name="change_password"),
]
