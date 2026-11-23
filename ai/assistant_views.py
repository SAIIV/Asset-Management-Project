"""AI #4 Assistant page (UC-30): ask a question, see the answer, rate it.

The chat lives in the user's session (last 6 turns) and is never stored with their name. Rating is only
offered for answers in the user's own chat, so nobody can rate another person's answer.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .assistant import MAX_QUESTION, ask, rate_answer

KEY = "assistant_chat"
KEEP = 6
EXAMPLES = [
    "Are there any laptops I can request?",
    "How do I request an item?",
    "What is happening with my requests?",
    "How do I report a broken item?",
]


def _back():
    return redirect(reverse("assistant:page") + "#latest")


@login_required
def page(request):
    chat = request.session.get(KEY, [])
    if request.method == "POST":
        if "clear" in request.POST:
            request.session.pop(KEY, None)
            return redirect("assistant:page")
        question = request.POST.get("question", "").strip()
        if not question:
            messages.warning(request, "Type a question first.")
            return redirect("assistant:page")
        history = [(turn["q"], turn["a"]) for turn in chat if not turn["fallback"]]
        answer = ask(request.user, question, history)
        chat.append({
            "q": question[:MAX_QUESTION],
            "a": answer.text,
            "message": answer.message,
            "fallback": answer.fallback,
            "items": [{"id": a.pk, "name": a.name, "dept": str(a.owner_department)} for a in answer.items],
            "page": list(answer.page) if answer.page else None,
            "record_id": answer.record_id,
            "model": answer.model,
            "rated": "",
        })
        request.session[KEY] = chat[-KEEP:]
        return _back()
    return render(request, "ai/assistant.html", {"chat": chat, "examples": EXAMPLES, "max_length": MAX_QUESTION})


@require_POST
@login_required
def rate(request, record_id):
    chat = request.session.get(KEY, [])
    turn = next((t for t in chat if t["record_id"] == record_id and not t["fallback"] and not t["rated"]), None)
    helpful = request.POST.get("helpful") == "yes"
    if turn is None or rate_answer(request.user, record_id, helpful) is None:
        messages.warning(request, "This answer cannot be rated.")
        return _back()
    turn["rated"] = "Helpful" if helpful else "Not helpful"
    request.session.modified = True
    messages.success(request, "Thanks for the feedback.")
    return _back()
