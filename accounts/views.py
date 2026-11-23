"""C1 Login and roles: sign-in page, sign-out and the starting view after sign-in."""

from django import forms
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import AuditLog
from .permissions import allowed_actions


class EmailSignInForm(AuthenticationForm):
    """The e-mail is not case sensitive: Requester@X and requester@x are the same account."""

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()


class SignInView(auth_views.LoginView):
    """UC-01 Sign in. A wrong password and a disabled account get the same generic message."""

    template_name = "registration/login.html"
    authentication_form = EmailSignInForm

    redirect_authenticated_user = True


class SignOutView(auth_views.LogoutView):
    """Ends the session (P3-NFR-SEC03). Only accepts POST, so a link cannot sign you out."""


class NameForm(forms.Form):
    name = forms.CharField(max_length=150, label="Full name")


@login_required
def account(request):
    """My account: change the display name or the password. E-mail, department and roles are set by the
    Administrator (Design Document Section 6), so they are shown but cannot be changed here."""
    from .services import AuditService

    user = request.user
    name_form = NameForm(initial={"name": user.name})
    if request.method == "POST":
        name_form = NameForm(request.POST)
        if name_form.is_valid():
            before, user.name = user.name, name_form.cleaned_data["name"].strip()
            user.save(update_fields=["name"])
            AuditService.log(user, "edit_profile", user, before={"name": before}, after={"name": user.name})
            messages.success(request, "Your name was updated.")
            return redirect("account")
    last = (AuditLog.objects.filter(user=user, action="change_password").order_by("-created_at").first())
    return render(request, "accounts/account.html", {
        "name_form": name_form, "password_changed_at": last.created_at if last else None})


@login_required
def change_password(request):
    """Its own page, opened from My account: old password, new password twice."""
    from .services import AuditService

    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        update_session_auth_hash(request, form.user)  # stay signed in
        AuditService.log(request.user, "change_password", request.user)  # never the password itself
        messages.success(request, "Your password was changed.")
        return redirect("account")
    return render(request, "accounts/change_password.html", {"form": form})


def home(request):
    """Starting view after sign-in: what needs your attention, quick actions, and what your roles allow.
    Visitors who are not signed in see the introductory page instead."""
    if not request.user.is_authenticated:
        from .home import intro_stats
        return render(request, "accounts/landing.html", {"stats": intro_stats()})
    from .home import quick_actions, tiles

    actions = allowed_actions(request.user)
    from .home import notices, recent_activity

    return render(request, "accounts/home.html", {
        "actions": actions, "tiles": tiles(request.user, actions), "quick": quick_actions(actions),
        "notices": notices(request.user), "activity": recent_activity(request.user),
    })
