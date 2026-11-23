"""AI #4 Assistant pages (UC-30): the full chat page and the small chat behind the bubble on every page.

Chats, photos and memory belong to one user: every view loads them with user=request.user, so another
person's chat answers 404. The bubble talks to the same views and asks for JSON (header X-Requested-With).
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .assistant import MAX_QUESTION
from .chat import ChatError, as_json, chats_of, forget, latest_chat, memory_of, rate, send
from .models import AssistantChat, AssistantMessage

EXAMPLES = [
    "Are there any laptops I can request?",
    "How do I request an item?",
    "What is happening with my requests?",
    "How do I report a broken item?",
]


def _wants_json(request):
    return request.headers.get("x-requested-with") == "fetch"


def _own_chat(request, pk):
    return get_object_or_404(AssistantChat, pk=pk, user=request.user)


def _render(request, chat):
    return render(request, "ai/assistant.html", {
        "chat": chat, "chat_messages": chat.messages.all() if chat else [],
        "chats": chats_of(request.user)[:30], "memory": memory_of(request.user),
        "examples": EXAMPLES, "max_length": MAX_QUESTION,
    })


@login_required
def page(request):
    """Pick up where the user left off: their most recent chat."""
    chat = latest_chat(request.user)
    return redirect("assistant:chat", pk=chat.pk) if chat else _render(request, None)


@login_required
def new_chat(request):
    return _render(request, None)


@login_required
def chat_page(request, pk):
    return _render(request, _own_chat(request, pk))


@require_POST
@login_required
def send_view(request):
    chat_id = request.POST.get("chat", "")
    chat = _own_chat(request, int(chat_id)) if chat_id.isdigit() else None
    try:
        question, reply = send(request.user, chat, request.POST.get("question", ""), request.FILES.get("photo"))
    except ChatError as error:
        if _wants_json(request):
            return JsonResponse({"error": str(error)}, status=400)
        messages.warning(request, str(error))
        return redirect(reverse("assistant:chat", args=[chat.pk]) if chat else reverse("assistant:new"))
    if _wants_json(request):
        return JsonResponse({"chat": reply.chat_id, "chat_url": reverse("assistant:chat", args=[reply.chat_id]),
                             "messages": [as_json(question), as_json(reply)]})
    return redirect(reverse("assistant:chat", args=[reply.chat_id]) + "#latest")


@login_required
def latest_json(request):
    """For the bubble: the user's most recent chat, so they can continue it."""
    chat = latest_chat(request.user)
    if chat is None:
        return JsonResponse({"chat": None, "messages": []})
    recent = list(chat.messages.order_by("-created_at", "-id")[:20])[::-1]
    return JsonResponse({"chat": chat.pk, "chat_url": reverse("assistant:chat", args=[chat.pk]),
                         "title": chat.title, "messages": [as_json(m) for m in recent]})


@require_POST
@login_required
def rate_view(request, pk):
    message = get_object_or_404(AssistantMessage.objects.select_related("chat"), pk=pk, chat__user=request.user)
    ok = rate(request.user, message, request.POST.get("helpful") == "yes")
    if _wants_json(request):
        return JsonResponse({"ok": ok, "rating": message.rating})
    if ok:
        messages.success(request, "Thanks for the feedback.")
    else:
        messages.warning(request, "This answer cannot be rated.")
    return redirect(reverse("assistant:chat", args=[message.chat_id]) + f"#m{message.pk}")


@login_required
def photo(request, pk):
    message = get_object_or_404(AssistantMessage, pk=pk, chat__user=request.user)
    if not message.photo:
        raise Http404
    return FileResponse(message.photo.open("rb"))


@require_POST
@login_required
def delete_chat(request, pk):
    chat = _own_chat(request, pk)
    for message in chat.messages.exclude(photo=""):
        message.photo.delete(save=False)
    chat.delete()
    messages.info(request, "Chat deleted.")
    return redirect("assistant:new")


@require_POST
@login_required
def forget_view(request):
    forget(request.user)
    messages.info(request, "The assistant's notes about you were cleared.")
    return redirect(request.POST.get("back") if str(request.POST.get("back", "")).startswith("/assistant/")
                    else "assistant:page")
