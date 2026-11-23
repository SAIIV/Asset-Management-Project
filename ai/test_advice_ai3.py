"""AI #3 Sustainable-action advice: facts, option check, fallback, and the follow / dismiss gate.

Gemini is never called: get_generator is replaced by a fake.
"""

from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, UserRole
from ai.advice import asset_facts, recommend_action
from ai.generators import AIUnavailable
from ai.models import AIRecord
from circular_campus.choices import AIDecision, AssetStatus as A
from circular_campus.test_utils import make_asset, make_department, make_user

PASSWORD = "Test-pass-123"


class Fake:
    name = "fake-gemini"

    def __init__(self, reply=None, error=None):
        self.reply, self.error = reply, error

    def generate(self, task, facts, schema, time_limit):
        if self.error:
            raise self.error
        return self.reply


def fake(reply=None, error=None):
    return patch("ai.advice.get_generator", return_value=Fake(reply, error))


def with_role(user, name):
    UserRole.objects.create(user=user, role=Role.objects.get_or_create(name=name)[0])
    return user


class AdviceTests(TestCase):
    def setUp(self):
        self.dept = make_department()
        self.custodian = with_role(make_user(department=self.dept, name="Private Person"), "Custodian")
        self.asset = make_asset(name="Old desk", owner_department=self.dept, status=A.AVAILABLE)

    def test_facts_describe_the_item_not_people(self):
        facts = asset_facts(self.asset)
        self.assertEqual(facts["item"], "Old desk")
        self.assertIn("repairCostSoFarAED", facts)
        self.assertNotIn("Private Person", str(facts))

    def test_valid_advice_is_recorded(self):
        with fake({"action": "Publish for reuse", "reason": "Works and is not needed.", "confidence": 0.8}):
            advice = recommend_action(self.asset)
        self.assertEqual(advice.action, "Publish for reuse")
        item = AIRecord.objects.get(pk=advice.record_id)
        self.assertFalse(item.unsure)
        self.assertEqual(item.output["action"], "Publish for reuse")

    def test_unknown_option_is_unsure_and_not_shown(self):
        with fake({"action": "Sell it", "reason": "money"}):
            advice = recommend_action(self.asset)
        self.assertTrue(advice.fallback)
        self.assertTrue(AIRecord.objects.get(pk=advice.record_id).unsure)

    def test_service_down_gives_fallback(self):
        with fake(error=AIUnavailable("timed out")):
            advice = recommend_action(self.asset)
        self.assertTrue(advice.fallback)
        self.assertIn("Advice unavailable", advice.message)

    def test_page_ask_then_follow(self):
        self.client.login(email=self.custodian.email, password=PASSWORD)
        with fake({"action": "Donate", "reason": "Nobody on campus asks for desks.", "confidence": 0.7}):
            response = self.client.post(reverse("advice:ask", args=[self.asset.pk]))
        record_id = AIRecord.objects.latest("pk").pk
        page = self.client.get(response["Location"])
        self.assertContains(page, "Nobody on campus asks for desks.")
        self.assertContains(page, "Follow this advice")
        self.client.post(reverse("advice:answer", args=[self.asset.pk, record_id]), {"decision": "accept"})
        self.assertEqual(AIRecord.objects.get(pk=record_id).decision, AIDecision.ACCEPTED)
        self.assertEqual(self.asset.__class__.objects.get(pk=self.asset.pk).status, A.AVAILABLE)  # nothing moved

    def test_other_department_cannot_ask(self):
        other = with_role(make_user(department=make_department()), "Custodian")
        self.client.login(email=other.email, password=PASSWORD)
        self.assertEqual(self.client.post(reverse("advice:ask", args=[self.asset.pk])).status_code, 403)
