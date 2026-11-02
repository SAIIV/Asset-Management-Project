"""Tests for SustainabilityImpact."""

from django.db import IntegrityError, transaction
from django.test import TestCase

from assets.models import MaintenanceRecord
from circular_campus.test_utils import make_asset, make_request, make_user, now
from reports.models import SustainabilityImpact
from transfers.models import Transfer


class SustainabilityImpactTests(TestCase):
    def test_exactly_one_source(self):
        asset = make_asset()
        transfer = Transfer.objects.create(asset=asset, request=make_request(), approver=make_user())
        repair = MaintenanceRecord.objects.create(asset=asset, reported_at=now(), action="fix")
        with self.assertRaises(IntegrityError), transaction.atomic():
            SustainabilityImpact.objects.create(avoided_cost_aed=100)
        with self.assertRaises(IntegrityError), transaction.atomic():
            SustainabilityImpact.objects.create(transfer=transfer, maintenance=repair, avoided_cost_aed=100)
        # avoidedCostAED may be negative; co2eKg may stay empty.
        impact = SustainabilityImpact.objects.create(transfer=transfer, avoided_cost_aed=-40)
        self.assertIsNone(impact.co2e_kg)
