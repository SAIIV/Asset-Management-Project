"""C7 Sustainability dashboard: Section 12 calculations and the Mockup 6 page."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, UserRole
from accounts.services import AuditService
from circular_campus.choices import ApprovalDecision as D, AssetStatus as A, TransferType
from circular_campus.test_utils import make_asset, make_category, make_department, make_user
from exchange.requests import RequestService
from reports.models import SustainabilityImpact
from reports.sustainability import co2e_for, dashboard, sync_impacts
from transfers.models import Transfer
from transfers.services import TransferService

PASSWORD = "Test-pass-123"


def with_role(user, name):
    UserRole.objects.create(user=user, role=Role.objects.get_or_create(name=name)[0])
    return user


class SustainabilityTests(TestCase):
    def setUp(self):
        self.chem, self.it = make_department(name="Chemistry"), make_department(name="IT Services")
        self.requester = with_role(make_user(department=self.chem), "Requester")
        self.custodian = with_role(make_user(department=self.it), "Custodian")
        self.approver = with_role(make_user(department=self.it), "Approver")
        self.admin = with_role(make_user(department=self.it), "Administrator")
        it_equipment = make_category(name="IT Equipment")
        self.monitors = make_category(name="Monitors", parent_category=it_equipment)

    def reuse(self, name, value=Decimal("800.00"), mass=Decimal("5.000")):
        """Publish, request, approve, release and receive one item. Returns the transfer."""
        asset = make_asset(name=name, owner_department=self.it, category=self.monitors, status=A.AVAILABLE,
                           is_listed=True, estimated_value_aed=value, mass_kg=mass)
        AuditService.log(self.custodian, "publish_asset", asset)
        req = RequestService.create(self.requester, {
            "purpose": "Lab screens", "quantity": 1, "required_by": date.today() + timedelta(days=7),
            "urgency": "Normal", "type": "Permanent", "mandatory_specs": [], "preferred_condition": "",
            "candidates": [asset],
        })
        TransferService.reserve(self.custodian, req, [asset])
        TransferService.decide(self.approver, req, D.APPROVED, "ok")
        transfer = Transfer.objects.get(asset=asset)
        TransferService.release(self.custodian, transfer)
        TransferService.receive(self.requester, transfer, "Good")
        return transfer

    def test_received_transfer_is_counted_once(self):
        transfer = self.reuse("Dell monitor")
        self.assertEqual(len(sync_impacts()), 1)
        self.assertEqual(sync_impacts(), [])  # safe to run again
        impact = SustainabilityImpact.objects.get(transfer=transfer)
        self.assertEqual((impact.avoided_cost_aed, impact.diverted_mass_kg), (Decimal("800.00"), Decimal("5.000")))
        self.assertFalse(impact.is_measured)

    def test_no_warm_factor_means_no_co2e(self):
        self.reuse("Dell monitor")
        sync_impacts()
        impact = SustainabilityImpact.objects.get()
        self.assertIsNone(impact.co2e_kg)
        self.assertIn("no EPA WARM v16 factor entered for IT Equipment", impact.factor_ref)
        self.assertEqual(dashboard()["no_co2e"], 1)

    def test_co2e_formula(self):
        with patch.dict("reports.sustainability.WARM_FACTORS", {"IT Equipment": 2.0}):
            kg, reference = co2e_for(Decimal("907.185"), self.monitors)  # one short ton
        self.assertEqual(kg, Decimal("2000.000"))  # 1 short ton x 2 MTCO2E x 1000
        self.assertIn("IT Equipment, 2.0 MTCO2E/short ton", reference)
        self.assertEqual(co2e_for(None, self.monitors)[0], None)

    def test_loan_is_not_counted(self):
        transfer = self.reuse("Loaned monitor")
        Transfer.objects.filter(pk=transfer.pk).update(type=TransferType.LOAN)
        self.assertEqual(sync_impacts(), [])
        self.assertEqual(dashboard()["reuse_count"], 0)

    def test_missing_baseline_is_reported_not_guessed(self):
        self.reuse("Old monitor", value=None)
        sync_impacts()
        figures = dashboard()
        self.assertEqual((figures["reuse_count"], figures["no_baseline"]), (1, 1))
        self.assertIsNone(figures["avoided_aed"])

    def test_dashboard_totals_rate_and_period(self):
        self.reuse("Monitor A", value=Decimal("500.00"), mass=Decimal("4.000"))
        self.reuse("Monitor B", value=Decimal("300.00"), mass=Decimal("6.000"))
        unused = make_asset(owner_department=self.it, category=self.monitors, status=A.AVAILABLE, is_listed=True)
        AuditService.log(self.custodian, "publish_asset", unused)
        sync_impacts()
        figures = dashboard()
        self.assertEqual((figures["reuse_count"], figures["avoided_aed"], figures["diverted_kg"]),
                         (2, Decimal("800.00"), Decimal("10.000")))
        self.assertEqual(figures["reuse_rate"], 66.7)  # 2 of 3 published items were reused
        self.assertEqual(figures["by_category"], [("IT Equipment", 2, 100)])
        self.assertEqual(dashboard(end=date.today() - timedelta(days=1))["reuse_count"], 0)

    def test_page_for_administrator(self):
        self.reuse("Dell monitor")
        self.client.login(email=self.admin.email, password=PASSWORD)
        page = self.client.get(reverse("reports:sustainability"))
        self.assertContains(page, "Dell monitor")
        self.assertContains(page, "AED 800.00")
        self.assertContains(page, "Unavailable")  # no WARM factor entered yet
        self.assertEqual(SustainabilityImpact.objects.count(), 1)  # the visit stored the impact

    def test_others_cannot_open_it(self):
        self.client.login(email=self.custodian.email, password=PASSWORD)
        self.assertEqual(self.client.get(reverse("reports:sustainability")).status_code, 403)

    def test_bad_period_shows_error(self):
        self.client.login(email=self.admin.email, password=PASSWORD)
        response = self.client.get(reverse("reports:sustainability"), {"start": "2026-12-01", "end": "2026-11-01"})
        self.assertContains(response, "start date is after the end date")
