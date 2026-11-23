"""AI #4 Assistant: retrieval, no invented items or links, privacy, fallback, saved chats, memory, photos.

Gemini is never called: get_generator is replaced by a fake.
"""

import shutil
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Role, UserRole
from ai.assistant import ask, find_items, user_facts
from ai.chat import ChatError, memory_of, send
from ai.generators import AIUnavailable
from ai.models import AIRecord, AssistantChat, AssistantMessage
from circular_campus.choices import AIDecision, AssetStatus as A
from circular_campus.test_utils import make_asset, make_department, make_user

PASSWORD = "Test-pass-123"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
MEDIA = tempfile.mkdtemp()


class Fake:
    name = "fake-gemini"

    def __init__(self, reply=None, error=None):
        self.reply, self.error, self.facts, self.images = reply, error, None, None

    def generate(self, task, facts, schema, time_limit, images=()):
        self.facts, self.images = facts, images
        if self.error:
            raise self.error
        return self.reply


def fake(reply=None, error=None, generator=None):
    return patch("ai.assistant.get_generator", return_value=generator or Fake(reply, error))


def with_role(user, name):
    UserRole.objects.create(user=user, role=Role.objects.get_or_create(name=name)[0])
    return user


@override_settings(MEDIA_ROOT=MEDIA)
class AssistantTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.mine, self.other = make_department(), make_department(name="Physics")
        self.user = with_role(make_user(department=self.mine, name="Private Person"), "Requester")
        self.laptop = make_asset(name="Dell laptop", owner_department=self.other, status=A.AVAILABLE, is_listed=True)
        self.own = make_asset(name="Our laptop", owner_department=self.mine, status=A.AVAILABLE, is_listed=True)
        self.hidden = make_asset(name="Hidden laptop", owner_department=self.other, status=A.AVAILABLE)
        self.chair = make_asset(name="Office chair", owner_department=self.other, status=A.AVAILABLE, is_listed=True)

    # ---- answers ----
    def test_finds_listed_items_of_other_departments_only(self):
        self.assertEqual(find_items(self.user, "Are there any laptops?"), [self.laptop])

    def test_facts_hold_no_name_or_email(self):
        facts = user_facts(self.user, [self.laptop])
        self.assertNotIn("Private Person", str(facts))
        self.assertNotIn(self.user.email, str(facts))
        self.assertIn("catalogue", facts["pagesYouCanOpen"])
        self.assertNotIn("approvals", facts["pagesYouCanOpen"])
        self.assertIn("Search listed assets", facts["whatYourRolesCanDo"])

    def test_answer_keeps_only_found_items_and_allowed_pages(self):
        reply = {"answer": "Physics has a Dell laptop.", "itemIds": [self.laptop.pk, self.chair.pk, 999],
                 "page": "approvals"}
        with fake(reply):
            answer = ask(self.user, "any laptop?")
        self.assertEqual(answer.items, [self.laptop])
        self.assertIsNone(answer.page)  # a Requester cannot open Approvals
        item = AIRecord.objects.get(pk=answer.record_id)
        self.assertTrue(item.unsure)
        self.assertEqual(item.output["dropped"], [self.chair.pk, 999])

    def test_service_down_gives_fallback(self):
        with fake(error=AIUnavailable("timed out")):
            answer = ask(self.user, "laptop")
        self.assertTrue(answer.fallback)
        self.assertIn("unavailable", answer.message)

    # ---- saved chats and memory ----
    def test_chat_is_saved_and_continued_with_history(self):
        with fake({"answer": "Physics has one.", "itemIds": [self.laptop.pk]}):
            question, reply = send(self.user, None, "laptop?")
        chat = question.chat
        self.assertEqual((chat.title, reply.items[0]["id"]), ("laptop?", self.laptop.pk))
        generator = Fake({"answer": "It is in good condition."})
        with fake(generator=generator):
            send(self.user, chat, "what condition is it in?")
        self.assertEqual(generator.facts["earlierInThisChat"], [{"q": "laptop?", "a": "Physics has one."}])
        self.assertEqual(chat.messages.count(), 4)

    def test_memory_note_is_kept_without_emails(self):
        with fake({"answer": "Noted.", "remember": "needs microscopes for a teaching lab"}):
            send(self.user, None, "we need microscopes for our teaching lab")
        with fake({"answer": "Ok.", "remember": "write to someone@example.com"}):
            send(self.user, None, "hello there")
        self.assertEqual(memory_of(self.user), ["needs microscopes for a teaching lab"])
        generator = Fake({"answer": "Here you go."})
        with fake(generator=generator):
            send(self.user, None, "anything new?")
        self.assertEqual(generator.facts["whatYouRememberAboutThisUser"], ["needs microscopes for a teaching lab"])

    def test_photo_is_sent_to_the_model_and_only_images_are_accepted(self):
        generator = Fake({"answer": "That looks like a projector."})
        with fake(generator=generator):
            question, _ = send(self.user, None, "", SimpleUploadedFile("p.png", PNG, "image/png"))
        self.assertEqual(generator.images[0][0], "image/png")
        self.assertTrue(question.photo)
        with self.assertRaisesMessage(ChatError, "Only JPEG"):
            send(self.user, None, "x", SimpleUploadedFile("evil.png", b"MZ not an image", "image/png"))

    # ---- pages ----
    def test_page_send_continue_and_rate_once(self):
        self.client.login(email=self.user.email, password=PASSWORD)
        with fake({"answer": "Physics has one.", "itemIds": [self.laptop.pk], "page": "none"}):
            self.client.post(reverse("assistant:send"), {"question": "laptop?"})
        chat = AssistantChat.objects.get(user=self.user)
        page = self.client.get(reverse("assistant:page"), follow=True)  # picks up the latest chat
        self.assertContains(page, "Physics has one.")
        self.assertContains(page, "Dell laptop")
        reply = chat.messages.get(role=AssistantMessage.ASSISTANT)
        self.client.post(reverse("assistant:rate", args=[reply.pk]), {"helpful": "yes"})
        self.assertEqual(AIRecord.objects.get(pk=reply.ai_record_id).decision, AIDecision.ACCEPTED)
        again = self.client.post(reverse("assistant:rate", args=[reply.pk]), {"helpful": "no"}, follow=True)
        self.assertContains(again, "cannot be rated")

    def test_bubble_gets_json(self):
        self.client.login(email=self.user.email, password=PASSWORD)
        with fake({"answer": "Hi!"}):
            data = self.client.post(reverse("assistant:send"), {"question": "hello there"},
                                    HTTP_X_REQUESTED_WITH="fetch").json()
        self.assertEqual([m["role"] for m in data["messages"]], ["user", "assistant"])
        latest = self.client.get(reverse("assistant:latest")).json()
        self.assertEqual(latest["chat"], data["chat"])
        self.assertContains(self.client.get(reverse("home")), "ai-bubble")

    def test_other_people_cannot_open_rate_or_see_a_chat(self):
        with fake({"answer": "Hi.", "itemIds": []}):
            question, reply = send(self.user, None, "hello there", SimpleUploadedFile("p.png", PNG, "image/png"))
        stranger = with_role(make_user(department=self.other), "Requester")
        self.client.login(email=stranger.email, password=PASSWORD)
        self.assertEqual(self.client.get(reverse("assistant:chat", args=[question.chat_id])).status_code, 404)
        self.assertEqual(self.client.get(reverse("assistant:photo", args=[question.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("assistant:rate", args=[reply.pk]), {"helpful": "no"}).status_code, 404)
        self.assertEqual(self.client.post(reverse("assistant:send"), {"chat": question.chat_id, "question": "x"}).status_code, 404)
        self.assertIsNone(AIRecord.objects.get(pk=reply.ai_record_id).decision)

    def test_page_needs_sign_in(self):
        self.assertEqual(self.client.get(reverse("assistant:page")).status_code, 302)
