"""AI #4 Assistant: retrieval, no invented items or links, privacy, fallback, the page and rating.

Gemini is never called: get_generator is replaced by a fake.
"""

from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, UserRole
from ai.assistant import ask, find_items, user_facts
from ai.generators import AIUnavailable
from ai.models import AIRecord
from circular_campus.choices import AIDecision, AssetStatus as A
from circular_campus.test_utils import make_asset, make_department, make_user

PASSWORD = "Test-pass-123"


class Fake:
    name = "fake-gemini"

    def __init__(self, reply=None, error=None):
        self.reply, self.error, self.facts = reply, error, None

    def generate(self, task, facts, schema, time_limit):
        self.facts = facts
        if self.error:
            raise self.error
        return self.reply


def fake(reply=None, error=None):
    return patch("ai.assistant.get_generator", return_value=Fake(reply, error))


def with_role(user, name):
    UserRole.objects.create(user=user, role=Role.objects.get_or_create(name=name)[0])
    return user


class AssistantTests(TestCase):
    def setUp(self):
        self.mine, self.other = make_department(), make_department(name="Physics")
        self.user = with_role(make_user(department=self.mine, name="Private Person"), "Requester")
        self.laptop = make_asset(name="Dell laptop", owner_department=self.other, status=A.AVAILABLE, is_listed=True)
        self.own = make_asset(name="Our laptop", owner_department=self.mine, status=A.AVAILABLE, is_listed=True)
        self.hidden = make_asset(name="Hidden laptop", owner_department=self.other, status=A.AVAILABLE)
        self.chair = make_asset(name="Office chair", owner_department=self.other, status=A.AVAILABLE, is_listed=True)

    def test_finds_listed_items_of_other_departments_only(self):
        found = find_items(self.user, "Are there any laptops?")
        self.assertEqual(found, [self.laptop])

    def test_facts_hold_no_name_or_email(self):
        facts = user_facts(self.user, [self.laptop])
        self.assertNotIn("Private Person", str(facts))
        self.assertNotIn(self.user.email, str(facts))
        self.assertIn("catalogue", facts["pagesYouCanOpen"])
        self.assertNotIn("approvals", facts["pagesYouCanOpen"])

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

    def test_good_answer_with_page(self):
        with fake({"answer": "Open the catalogue.", "itemIds": [], "page": "catalogue"}):
            answer = ask(self.user, "how do I get a chair?")
        self.assertEqual(answer.page, ("Browse the catalogue", reverse("exchange:catalogue")))
        self.assertFalse(AIRecord.objects.get(pk=answer.record_id).unsure)

    def test_service_down_gives_fallback(self):
        with fake(error=AIUnavailable("timed out")):
            answer = ask(self.user, "laptop")
        self.assertTrue(answer.fallback)
        self.assertIn("unavailable", answer.message)
        self.assertTrue(AIRecord.objects.get(pk=answer.record_id).fallback)

    def test_page_ask_and_rate_once(self):
        self.client.login(email=self.user.email, password=PASSWORD)
        with fake({"answer": "Physics has one.", "itemIds": [self.laptop.pk], "page": "none"}):
            self.client.post(reverse("assistant:page"), {"question": "laptop?"})
        page = self.client.get(reverse("assistant:page"))
        self.assertContains(page, "Physics has one.")
        self.assertContains(page, "Dell laptop")
        record_id = AIRecord.objects.latest("pk").pk
        self.client.post(reverse("assistant:rate", args=[record_id]), {"helpful": "yes"})
        self.assertEqual(AIRecord.objects.get(pk=record_id).decision, AIDecision.ACCEPTED)
        again = self.client.post(reverse("assistant:rate", args=[record_id]), {"helpful": "no"}, follow=True)
        self.assertContains(again, "cannot be rated")
        self.assertEqual(AIRecord.objects.get(pk=record_id).decision, AIDecision.ACCEPTED)

    def test_cannot_rate_someone_elses_answer(self):
        with fake({"answer": "Hi.", "itemIds": []}):
            answer = ask(self.user, "hello there")
        stranger = make_user(department=self.other)
        self.client.login(email=stranger.email, password=PASSWORD)
        self.client.post(reverse("assistant:rate", args=[answer.record_id]), {"helpful": "no"})
        self.assertIsNone(AIRecord.objects.get(pk=answer.record_id).decision)

    def test_page_needs_sign_in(self):
        response = self.client.get(reverse("assistant:page"))
        self.assertEqual(response.status_code, 302)
