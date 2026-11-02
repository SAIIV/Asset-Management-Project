"""UC-01 Sign in: every sign-in, failed attempt and sign-out is written to the audit log."""

from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from .services import AuditService


@receiver(user_logged_in)
def record_sign_in(sender, request, user, **kwargs):
    AuditService.log(user, "sign_in", user)


@receiver(user_logged_out)
def record_sign_out(sender, request, user, **kwargs):
    if user is not None:
        AuditService.log(user, "sign_out", user)


@receiver(user_login_failed)
def record_failed_sign_in(sender, credentials, request=None, **kwargs):
    # Only the email is looked at; the password is never stored.
    email = (credentials or {}).get("username") or (credentials or {}).get("email") or ""
    account = get_user_model().objects.filter(email__iexact=email).first()
    AuditService.log(
        None, "sign_in_failed", record_type="User", record_id=account.pk if account else 0,
        reason="Wrong password or disabled account" if account else "Unknown email",
    )
