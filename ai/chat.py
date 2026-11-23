"""AI #4 Assistant conversations: each user keeps their own chats and a short memory, and can pick up
where they left off from the chat page or the bubble on every page.

    send(user, chat, text, photo=None) -> (question message, answer message)
    chats_of(user), latest_chat(user), memory_of(user), forget(user), rate(user, message, helpful)

Privacy (Section 3.3): chats, photos and memory are only ever loaded for their owner. Gemini receives the
question, the photo, the last turns of this chat and the memory notes, never a name or e-mail address.
"""

from django.db import transaction

from .assistant import MEMORY_LIMIT, ask, rate_answer
from .models import AssistantChat, AssistantMemory, AssistantMessage

MAX_PHOTO_BYTES = 5 * 1024 * 1024
PHOTO_TYPES = {"image/jpeg": b"\xff\xd8\xff", "image/png": b"\x89PNG", "image/webp": b"RIFF", "image/gif": b"GIF8"}
HISTORY_TURNS = 4


class ChatError(Exception):
    """Shown to the user; nothing was sent."""


def chats_of(user):
    return AssistantChat.objects.filter(user=user)


def latest_chat(user):
    return chats_of(user).first()


def memory_of(user):
    memory = AssistantMemory.objects.filter(user=user).first()
    return memory.notes if memory else []


def forget(user):
    AssistantMemory.objects.filter(user=user).delete()


def _remember(user, note):
    if not note:
        return
    memory, _ = AssistantMemory.objects.get_or_create(user=user)
    notes = [n for n in memory.notes if n.lower() != note.lower()] + [note]
    memory.notes = notes[-MEMORY_LIMIT:]
    memory.save()


def check_photo(photo):
    """(mime, bytes) of an allowed photo, or raises ChatError. None if no photo was attached."""
    if not photo:
        return None
    if photo.size > MAX_PHOTO_BYTES:
        raise ChatError("The photo is larger than 5 MB. Please send a smaller one.")
    data = photo.read()
    photo.seek(0)
    mime = next((m for m, magic in PHOTO_TYPES.items() if data.startswith(magic)), None)
    if mime is None or (mime == "image/webp" and data[8:12] != b"WEBP"):
        raise ChatError("Only JPEG, PNG, WebP or GIF photos can be sent.")
    return mime, data


def history_of(chat):
    """The last question/answer pairs of this chat, oldest first."""
    pairs, question = [], None
    for message in chat.messages.order_by("created_at", "id"):
        if message.role == AssistantMessage.USER:
            question = message.text or "(photo)"
        elif question is not None and not message.fallback:
            pairs.append((question, message.text))
            question = None
    return pairs[-HISTORY_TURNS:]


def send(user, chat, text, photo=None):
    """Ask the assistant inside chat (a new chat is started when chat is None)."""
    text = (text or "").strip()
    image = check_photo(photo)
    if not text and image is None:
        raise ChatError("Type a question or attach a photo first.")
    with transaction.atomic():
        if chat is None:
            chat = AssistantChat.objects.create(user=user)
        if not chat.title:
            chat.title = (text or "Photo question")[:80]
        history = history_of(chat)
        question = AssistantMessage.objects.create(chat=chat, role=AssistantMessage.USER, text=text,
                                                   photo=photo or "")
    answer = ask(user, text, history, image=image, memory=memory_of(user))  # outside the transaction: slow call
    reply = AssistantMessage.objects.create(
        chat=chat, role=AssistantMessage.ASSISTANT, fallback=answer.fallback,
        text=answer.message if answer.fallback else answer.text,
        items=[{"id": a.pk, "name": a.name, "dept": str(a.owner_department)} for a in answer.items],
        page=list(answer.page) if answer.page else None, ai_record_id=answer.record_id)
    _remember(user, answer.remember)
    chat.save()  # moves the chat to the top of the list
    return question, reply


def rate(user, message, helpful):
    """Helpful / Not helpful on one of the user's own answers, once."""
    if message.chat.user_id != user.pk or message.role != AssistantMessage.ASSISTANT or message.fallback \
            or message.rating or not message.ai_record_id:
        return False
    if rate_answer(user, message.ai_record_id, helpful) is None:
        return False
    message.rating = "Helpful" if helpful else "Not helpful"
    message.save(update_fields=["rating"])
    return True


def as_json(message):
    from django.urls import reverse

    return {
        "id": message.pk, "role": message.role, "text": message.text, "fallback": message.fallback,
        "items": [dict(item, url=reverse("exchange:catalogue_detail", args=[item["id"]])) for item in message.items],
        "page": message.page, "rating": message.rating,
        "photo": reverse("assistant:photo", args=[message.pk]) if message.photo else None,
        "rate": reverse("assistant:rate", args=[message.pk]),
    }
