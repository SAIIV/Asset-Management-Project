"""C8 Inbox: every signed-in user sees only their own messages (any role)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Notification
from .services import link_of, mark_all_read, mark_read


@login_required
def inbox(request):
    notes = Notification.objects.filter(user=request.user)
    if request.GET.get("show") == "unread":
        notes = notes.filter(read_at__isnull=True)
    page = Paginator(notes.order_by("-created_at", "-id"), 25).get_page(request.GET.get("page"))
    for note in page:
        note.link = link_of(note)
    return render(request, "notifications/inbox.html", {"page": page, "show": request.GET.get("show", "")})


@login_required
@require_POST
def open_notification(request, pk):
    """Mark the message read and go to the record it is about.

    The lookup includes user=request.user, so another user's message gives 404.
    """
    note = get_object_or_404(Notification, pk=pk, user=request.user)
    mark_read(note)
    return redirect(link_of(note) or "notifications:inbox")


@login_required
@require_POST
def read_all(request):
    count = mark_all_read(request.user)
    messages.success(request, f"{count} message{'s' if count != 1 else ''} marked as read.")
    return redirect("notifications:inbox")
