"""C8 Notifications: the one way to send an in-app message (Phase 6 plan, Section 4.1).

    notify(user, "Request #12 was approved.", record=request)
    notify_many(custodians, "New request for your asset.", record=request)

C4 (request made) and C5 (approved, rejected, received) call these. A message
is linked to the record it is about as "<Table>:<id>", e.g. "ResourceRequest:12",
so the inbox can open that record. E-mail notifications are a later increment
(Design Document Section 6.5); Prototype 1 only has the in-app inbox.
"""

from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from .models import Notification

#: Table name -> URL name of the page that shows one record of it.
#: Each feature adds its own page here when it exists (C4 adds ResourceRequest, C5 adds Transfer).
RECORD_PAGES = {
    "Asset": "assets:detail",
    "ResourceRequest": "exchange:request_detail",

}


def record_label(record):
    """ "<Table>:<id>" for a record. Asset subtypes (ITAsset, ...) are written as Asset."""
    if record is None:
        return ""
    name = type(record).__name__
    for cls in type(record).__mro__:
        if cls.__name__ == "Asset":
            name = "Asset"
    return f"{name}:{record.pk}"


def notify(user, message, record=None):
    """Put one message in one user's inbox. Inactive users get nothing."""
    if user is None or not user.is_active:
        return None
    return Notification.objects.create(user=user, message=message[:1000], linked_record=record_label(record))


def notify_many(users, message, record=None):
    """The same message to several users (each user once)."""
    sent, seen = [], set()
    for user in users:
        if user is not None and user.pk not in seen:
            seen.add(user.pk)
            note = notify(user, message, record)
            if note:
                sent.append(note)
    return sent


def unread_count(user):
    if not getattr(user, "is_authenticated", False):
        return 0
    return Notification.objects.filter(user=user, read_at__isnull=True).count()


def link_of(notification):
    """URL of the record the message is about, or None if it has no page (yet)."""
    table, _, pk = notification.linked_record.partition(":")
    url_name = RECORD_PAGES.get(table)
    if not url_name or not pk.isdigit():
        return None
    try:
        return reverse(url_name, args=[int(pk)])
    except NoReverseMatch:
        return None


def mark_read(notification):
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at"])
    return notification


def mark_all_read(user):
    return Notification.objects.filter(user=user, read_at__isnull=True).update(read_at=timezone.now())
