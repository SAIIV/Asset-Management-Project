"""C1 Login and roles: sign-in page, sign-out and the starting view after sign-in."""

from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .permissions import allowed_actions


class SignInView(auth_views.LoginView):
    """UC-01 Sign in. A wrong password and a disabled account get the same generic message."""

    template_name = "registration/login.html"
    redirect_authenticated_user = True


class SignOutView(auth_views.LogoutView):
    """Ends the session (P3-NFR-SEC03). Only accepts POST, so a link cannot sign you out."""


@login_required
def home(request):
    """Starting view after sign-in: who you are, your roles and what they allow."""
    return render(request, "accounts/home.html", {"actions": allowed_actions(request.user)})
