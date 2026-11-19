"""AI #1 Classification and tagging: suggestion, unsure rules, fallback and the Register form.

The real model is never loaded in tests: a small fake embedder gives each
known word its own direction, so the expected similarities are exact.
"""

import re
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, UserRole
from ai import classify
from ai.classify import classify_asset
from ai.embeddings import EmbeddingUnavailable, cosine
from ai.models import AIRecord, ModelVersion
from assets.models import Asset
from circular_campus.test_utils import make_asset, make_category, make_department, make_user

PASSWORD = "Test-pass-123"
AXES = {"laptop": 0, "laptops": 0, "notebook": 0, "monitor": 1, "monitors": 1, "screen": 1, "chair": 2, "chairs": 2}


class FakeEmbedder:
    name = "fake-embedder"

    def embed(self, texts):
        vectors = []
        for text in texts:
            vector = [0.0] * 384
            for word in re.findall(r"[a-z]+", text.lower()):
                if word in AXES:
                    vector[AXES[word]] += 1
            vectors.append(vector)
        return vectors


def with_role(user, name):
    UserRole.objects.create(user=user, role=Role.objects.get_or_create(name=name)[0])
    return user


@patch("ai.classify.get_embedder", lambda: FakeEmbedder())
class ClassifyTests(TestCase):
    def setUp(self):
        classify._stamps.clear()
        classify._example_vectors.clear()
        self.dept = make_department()
        it = make_category(name="IT Equipment")
        self.laptops = make_category(name="Laptops", parent_category=it)
        self.monitors = make_category(name="Monitors", parent_category=it)
        self.chairs = make_category(name="Office chairs", parent_category=make_category(name="Furniture"))
        make_asset(name="Dell notebook", category=self.laptops, owner_department=self.dept, tags=["Laptop", "16GB"])
        make_asset(name="HP notebook", category=self.laptops, owner_department=self.dept, tags=["laptop"])

    def test_confident_suggestion_with_tags(self):
        suggestion = classify_asset("Lenovo laptop", "Thin notebook, 16GB")
        self.assertEqual(suggestion.category, self.laptops)
        self.assertFalse(suggestion.unsure)
        self.assertEqual(suggestion.tags[0], "laptop")
        self.assertEqual(len(suggestion.ranked), 3)
        item = AIRecord.objects.get(pk=suggestion.record_id)
        self.assertEqual((item.task, item.output["categoryId"], item.fallback), ("classify_asset", self.laptops.pk, False))
        self.assertEqual(item.model_version.thresholds, {"min_similarity": 0.60, "min_lead": 0.10})

    def test_close_call_is_unsure(self):
        suggestion = classify_asset("Laptop with monitor")  # equally close to both: lead 0 < 0.10
        self.assertTrue(suggestion.unsure)
        self.assertIsNone(suggestion.category)
        self.assertEqual(suggestion.message, "Low confidence, please choose.")
        self.assertIsNone(AIRecord.objects.get(pk=suggestion.record_id).output["categoryId"])

    def test_low_similarity_is_unsure(self):
        suggestion = classify_asset("Banana")  # similarity 0 < 0.60
        self.assertTrue(suggestion.unsure)
        self.assertIsNone(suggestion.category)

    def test_material_found_in_text(self):
        suggestion = classify_asset("Oak chair", "Solid wood office chair")
        self.assertEqual((suggestion.category, suggestion.material), (self.chairs, "wood"))

    def test_category_vectors_are_stored_and_reused(self):
        classify_asset("Laptop")
        self.assertIsNotNone(type(self.laptops).objects.get(pk=self.laptops.pk).embedding)
        classify_asset("Monitor")
        self.assertEqual(ModelVersion.objects.filter(kind="Embedding").count(), 1)  # same settings, same row

    def test_cosine(self):
        self.assertAlmostEqual(cosine([1, 0], [1, 0]), 1.0)
        self.assertEqual(cosine([0, 0], [1, 0]), 0.0)


class FallbackTests(TestCase):
    def test_model_missing_gives_fallback(self):
        def unavailable():
            raise EmbeddingUnavailable("the sentence-transformers library is not installed")

        with patch("ai.classify.get_embedder", unavailable):
            suggestion = classify_asset("Lenovo laptop")
        self.assertTrue(suggestion.fallback)
        self.assertIn("Suggestions unavailable", suggestion.message)
        self.assertTrue(AIRecord.objects.get(pk=suggestion.record_id).fallback)

    def test_switched_off_in_settings(self):
        with self.settings(AI_EMBEDDINGS="off"):
            self.assertTrue(classify_asset("Lenovo laptop").fallback)


@patch("ai.classify.get_embedder", lambda: FakeEmbedder())
class RegisterFormTests(TestCase):
    def setUp(self):
        classify._stamps.clear()
        classify._example_vectors.clear()
        self.dept = make_department()
        it = make_category(name="IT Equipment")
        self.laptops = make_category(name="Laptops", parent_category=it)
        self.monitors = make_category(name="Monitors", parent_category=it)
        self.custodian = with_role(make_user(department=self.dept), "Custodian")
        self.client.login(email=self.custodian.email, password=PASSWORD)
        self.data = {
            "name": "Lenovo laptop", "kind": "it", "status": "Available", "condition": "Good", "category": "",
            "serial_number": "SN-AI-001", "tags_text": "", "description": "Thin notebook", "campus": "Main",
            "building": "B1", "room": "101", "purchase_date": "", "estimated_value_aed": "", "mass_kg": "",
            "calibration_due": "", "material": "",
        }

    def suggest(self):
        response = self.client.post(reverse("assets:create"), {**self.data, "suggest": "1"})
        self.assertContains(response, "AI suggestion")
        self.assertEqual(Asset.objects.count(), 0)  # nothing is saved by a suggestion
        return response.context["form"].initial

    def test_suggestion_keeps_typed_data_and_preselects(self):
        initial = self.suggest()
        self.assertEqual((initial["category"], initial["name"], initial["serial_number"]),
                         (self.laptops.pk, "Lenovo laptop", "SN-AI-001"))

    def test_keeping_the_suggestion_is_accepted(self):
        initial = self.suggest()
        self.client.post(reverse("assets:create"), {**self.data, "category": self.laptops.pk,
                                                    "ai_record": initial["ai_record"]})
        self.assertEqual(Asset.objects.get().category, self.laptops)
        self.assertEqual(AIRecord.objects.get(pk=initial["ai_record"]).decision, "Accepted")

    def test_changing_the_category_is_corrected(self):
        initial = self.suggest()
        self.client.post(reverse("assets:create"), {**self.data, "category": self.monitors.pk,
                                                    "ai_record": initial["ai_record"]})
        self.assertEqual(AIRecord.objects.get(pk=initial["ai_record"]).decision, "Corrected")
