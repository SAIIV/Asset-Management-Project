"""Makes `unread_count` available in every template, for the Inbox menu badge."""

from .services import unread_count


def inbox(request):
    return {"unread_count": unread_count(getattr(request, "user", None))}
