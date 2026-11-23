"""AI #2 Matching and ranking: filter, five factors, weights, explanation, fallback and gate 2.

The real model is never loaded in tests: a fake embedder gives each known word
its own direction, so similarities are exactly 1 or 0 and the scores can be
worked out by hand (Section 11.2).
"""

import re
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, UserRole
from ai import matching
from ai.matching import condition_fit, rank_matches, ready_fit
from ai.models import AIRecord
from circular_campus.choices import AssetStatus as A
from circular_campus.test_utils import make_asset, make_category, make_department, make_user
from exchange.models import MatchRecommendation, ResourceRequest

PASSWORD = "Test-pass-123"
AXES = {"laptop": 0, "monitor": 1, "monitors": 1, "screen": 1, "screens": 1, "chair": 2, "chairs": 2}


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


@patch("ai.matching.get_embedder", lambda: FakeEmbedder())
class RankingTests(TestCase):
    def setUp(self):
        matching._stamps.clear()
        self.chem, self.it = make_department(name="Chemistry"), make_department(name="IT Services")
        self.requester = with_role(make_user(department=self.chem), "Requester")
        screens, seats = make_category(name="Displays"), make_category(name="Seating")

        def unit(name, description, condition, mass, category=screens, department=self.it):
            return make_asset(name=name, description=description, condition=condition, category=category,
                              mass_kg=mass, owner_department=department, status=A.AVAILABLE, is_listed=True)

        self.dell = unit("Dell monitor", "24 inch screen with HDMI", "Good", Decimal("5"))
        self.old = unit("Old monitor", "VGA only", "NeedsRepair", Decimal("4"))
        self.chair = unit("Office chair", "Mesh back", "Fair", Decimal("10"), category=seats)
        unit("Own monitor", "Our own department's", "Good", Decimal("5"), department=self.chem)  # never offered
        self.required_by = date.today() + timedelta(days=10)

    def rank(self, purpose="Second screens for the lab", specs=(), preferred="Good", urgency="Normal", quantity=1):
        return rank_matches(self.requester, purpose, list(specs), quantity, self.required_by, urgency, preferred)

    def test_scores_follow_section_11(self):
        ranking = self.rank()
        # C is not recorded, so its weight is shared out: S .50, T .22, R .17, E .11
        self.assertEqual([(m.asset.name, m.score) for m in ranking.matches],
                         [("Dell monitor", 94), ("Old monitor", 71), ("Office chair", 39)])
        dell = ranking.matches[0]
        self.assertEqual((dell.factors["S"], dell.factors["T"], dell.factors["R"], dell.factors["C"], dell.factors["E"]),
                         (1.0, 1.0, 1.0, None, 0.5))
        self.assertEqual(ranking.top_pick, dell)
        self.assertEqual(dell.label, "Strong match")
        self.assertIn("close in purpose to your request (similarity 1.00)", dell.reasons)
        self.assertIn("Weak match", ranking.matches[2].warnings)
        self.assertIn("C", ranking.dropped)

    def test_mandatory_specs_filter_first(self):
        ranking = self.rank(specs=["HDMI"])
        self.assertEqual([m.asset for m in ranking.matches], [self.dell])
        self.assertEqual({a for a, _ in ranking.excluded}, {self.old, self.chair})
        self.assertIn("Only 1 eligible unit(s) for the 2 you need.", self.rank(specs=["HDMI"], quantity=2).warnings)

    def test_missing_mass_drops_e_for_everyone(self):
        type(self.chair).objects.filter(pk=self.chair.pk).update(mass_kg=None)
        ranking = self.rank()
        self.assertIn("E", ranking.dropped)
        self.assertTrue(all(m.factors["E"] is None for m in ranking.matches))
        self.assertEqual(ranking.matches[0].score, 100)  # S, T and R all 1

    def test_weak_list_has_no_top_pick(self):
        ranking = self.rank(purpose="Bananas")
        self.assertIsNone(ranking.top_pick)
        self.assertTrue(AIRecord.objects.get(pk=ranking.record_id).unsure)
        self.assertTrue(any("No strong match" in w for w in ranking.warnings))

    def test_ties_ordered_by_asset_id(self):
        type(self.old).objects.filter(pk=self.old.pk).update(mass_kg=Decimal("5"))  # now equal to the Dell
        ranking = self.rank(purpose="Bananas", preferred="")
        tied = [m for m in ranking.matches if m.asset in (self.dell, self.old)]
        self.assertEqual(tied[0].score, tied[1].score)  # 44 each; the heavier chair scores 50 and comes first
        self.assertEqual([m.asset for m in tied], [self.dell, self.old])

    def test_similar_units_come_before_dissimilar_ones(self):
        # Only a little similar (0.45) and in poor condition: score 22, below the chair's 39.
        # The chair's purpose is not similar at all (0.00), so it still comes after (Section 4, service 2).
        mixed = make_asset(name="Laptop laptop monitor", condition="NeedsRepair", mass_kg=Decimal("1"),
                           category=self.dell.category, owner_department=self.it, status=A.AVAILABLE, is_listed=True)
        ranking = self.rank(purpose="Monitor screen")
        names = [m.asset for m in ranking.matches]
        self.assertLess(names.index(mixed), names.index(self.chair))
        self.assertLess(next(m.score for m in ranking.matches if m.asset == mixed),
                        next(m.score for m in ranking.matches if m.asset == self.chair))

    def test_seed_words_are_not_compared(self):
        seeded = make_asset(name="Dell laptop (synthetic #001)", category=self.dell.category, tags=["synthetic", "laptops"],
                            description="SYNTHETIC test record #001. Dell laptop for Circular Campus development.")
        text = matching.asset_text(seeded)
        self.assertNotIn("synthetic", text.lower())
        self.assertIn("Dell laptop", text)

    def test_factor_rules(self):

        self.assertEqual((condition_fit("Good", "Good"), condition_fit("Fair", "Good"), condition_fit("NeedsRepair", "Good"),
                          condition_fit("Fair", "")), (1.0, 0.5, 0.0, 1.0))
        today = date(2026, 11, 20)
        self.assertEqual(ready_fit(today + timedelta(days=5), "High", today), 1.0)
        self.assertAlmostEqual(ready_fit(today + timedelta(days=1), "High", today), 0.6)
        self.assertEqual(ready_fit(today, "Low", today), 1.0)

    def test_record_and_vectors(self):
        ranking = self.rank()
        item = AIRecord.objects.get(pk=ranking.record_id)
        self.assertEqual((item.task, item.fallback, item.score), ("rank_matches", False, Decimal("94")))
        self.assertEqual([row["assetId"] for row in item.output["ranked"]], [self.dell.pk, self.old.pk, self.chair.pk])
        self.assertEqual(item.model_version.weights, {"S": 0.45, "T": 0.20, "R": 0.15, "C": 0.10, "E": 0.10})
        self.assertIsNotNone(type(self.dell).objects.get(pk=self.dell.pk).embedding)


class RankingFallbackTests(TestCase):
    def test_not_ranked_when_model_is_off(self):
        it, chem = make_department(), make_department()
        requester = with_role(make_user(department=chem), "Requester")
        first = make_asset(owner_department=it, status=A.AVAILABLE, is_listed=True)
        second = make_asset(owner_department=it, status=A.AVAILABLE, is_listed=True)
        with self.settings(AI_EMBEDDINGS="off"):
            ranking = rank_matches(requester, "Screens", [], 1, date.today() + timedelta(days=3), "Normal")
        self.assertTrue(ranking.fallback)
        self.assertIn("Not ranked", ranking.message)
        self.assertEqual([m.asset for m in ranking.matches], [first, second])  # Asset ID order


@patch("ai.matching.get_embedder", lambda: FakeEmbedder())
class RequestFormTests(TestCase):
    def setUp(self):
        matching._stamps.clear()
        chem, it = make_department(), make_department()
        self.requester = with_role(make_user(department=chem), "Requester")
        screens = make_category(name="Displays")
        self.dell = make_asset(name="Dell monitor", description="screen", condition="Good", mass_kg=Decimal("5"),
                               category=screens, owner_department=it, status=A.AVAILABLE, is_listed=True)
        self.old = make_asset(name="Old monitor", condition="NeedsRepair", mass_kg=Decimal("4"),
                              category=screens, owner_department=it, status=A.AVAILABLE, is_listed=True)
        self.client.login(email=self.requester.email, password=PASSWORD)
        self.data = {"purpose": "Second screens", "quantity": "1",
                     "required_by": str(date.today() + timedelta(days=10)), "urgency": "Normal",
                     "type": "Permanent", "mandatory_specs_text": "", "preferred_condition": "Good"}

    def find(self):
        response = self.client.post(reverse("exchange:request_create"), {**self.data, "find_matches": "1"})
        self.assertContains(response, "AI ranking")
        self.assertContains(response, "Strong match")
        self.assertEqual(ResourceRequest.objects.count(), 0)  # nothing saved, nothing ticked for the requester
        self.assertEqual(response.context["ticked"], [])
        return response.context["form"].initial["ai_record"]

    def submit(self, record_id, chosen):
        self.client.post(reverse("exchange:request_create"),
                         {**self.data, "candidates": [a.pk for a in chosen], "ai_record": record_id, "submit": "1"})
        return ResourceRequest.objects.get()

    def test_choosing_the_top_unit_is_accepted(self):
        record_id = self.find()
        request = self.submit(record_id, [self.dell])
        rows = MatchRecommendation.objects.filter(request=request, ai_record_id=record_id)
        self.assertEqual([(r.asset, r.rank_position, r.decision) for r in rows],
                         [(self.dell, 1, "Accepted"), (self.old, 2, None)])
        self.assertEqual(AIRecord.objects.get(pk=record_id).decision, "Accepted")

    def test_choosing_another_unit_is_corrected(self):
        record_id = self.find()
        self.submit(record_id, [self.old])
        self.assertEqual(AIRecord.objects.get(pk=record_id).decision, "Corrected")

    def test_choosing_nothing_is_rejected(self):
        record_id = self.find()
        self.submit(record_id, [])
        self.assertEqual(AIRecord.objects.get(pk=record_id).decision, "Rejected")

    def test_purpose_needed_first(self):
        response = self.client.post(reverse("exchange:request_create"),
                                    {**self.data, "purpose": "", "find_matches": "1"}, follow=True)
        self.assertContains(response, "Type the purpose")
