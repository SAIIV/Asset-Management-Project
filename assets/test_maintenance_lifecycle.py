"""Maintenance and lifecycle (UC-19 to UC-25): faults, repairs and donation / recycling / disposal."""

from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, UserRole
from assets.maintenance import LifecycleService, MaintenanceError, MaintenanceService
from assets.models import Asset
from circular_campus.choices import (
    AssetStatus as A,
    LifecycleActionType as K,
    LifecycleStatus as L,
    MaintenanceStatus as M,
)
from circular_campus.test_utils import make_asset, make_department, make_user
from notifications.models import Notification

PASSWORD = "Test-pass-123"


def with_role(user, *names):
    for name in names:
        UserRole.objects.create(user=user, role=Role.objects.get_or_create(name=name)[0])
    return user


class Setup(TestCase):
    def setUp(self):
        self.it, self.chem = make_department(name="IT"), make_department(name="Chemistry")
        self.custodian = with_role(make_user(department=self.it), "Custodian")
        self.requester = with_role(make_user(department=self.chem), "Requester")
        self.approver = with_role(make_user(department=self.chem), "Approver")
        self.chair = make_asset(name="Office chair", owner_department=self.it, status=A.AVAILABLE, is_listed=True)

    def status(self, obj):
        return type(obj).objects.get(pk=obj.pk).status


class FaultTests(Setup):
    def test_report_tells_the_custodian_and_blocks_a_second_report(self):
        record = MaintenanceService.report_fault(self.requester, self.chair, "wheel broken")
        self.assertEqual(record.status, M.REPORTED)
        self.assertTrue(Notification.objects.filter(user=self.custodian, message__contains="wheel broken").exists())
        with self.assertRaisesMessage(MaintenanceError, "already open"):
            MaintenanceService.report_fault(self.requester, self.chair, "still broken")

    def test_repair_takes_item_off_the_catalogue_and_brings_it_back(self):
        record = MaintenanceService.report_fault(self.requester, self.chair, "wheel broken")
        MaintenanceService.start_repair(self.custodian, record)
        chair = Asset.objects.get(pk=self.chair.pk)
        self.assertEqual((chair.status, chair.is_listed), (A.UNDER_MAINTENANCE, False))
        MaintenanceService.finish_repair(self.custodian, record, "45.50", "new wheel")
        record.refresh_from_db()
        self.assertEqual((record.status, str(record.cost)), (M.COMPLETED, "45.50"))
        self.assertEqual(self.status(self.chair), A.AVAILABLE)
        self.assertTrue(Notification.objects.filter(user=self.requester, message__contains="repaired").exists())

    def test_item_in_use_goes_back_to_in_use(self):
        Asset.objects.filter(pk=self.chair.pk).update(status=A.IN_USE, is_listed=False)
        record = MaintenanceService.report_fault(self.custodian, self.chair, "armrest loose")
        MaintenanceService.start_repair(self.custodian, record)
        MaintenanceService.finish_repair(self.custodian, record)
        self.assertEqual(self.status(self.chair), A.IN_USE)

    def test_reserved_item_is_not_moved(self):
        Asset.objects.filter(pk=self.chair.pk).update(status=A.RESERVED)
        record = MaintenanceService.report_fault(self.requester, self.chair, "scratched")
        with self.assertRaisesMessage(MaintenanceError, "Finish its request"):
            MaintenanceService.start_repair(self.custodian, record)

    def test_negative_cost_and_closing_without_reason_are_refused(self):
        record = MaintenanceService.report_fault(self.requester, self.chair, "wobbly")
        with self.assertRaises(MaintenanceError):
            MaintenanceService.cancel(self.custodian, record, "")
        MaintenanceService.start_repair(self.custodian, record)
        with self.assertRaisesMessage(MaintenanceError, "negative"):
            MaintenanceService.finish_repair(self.custodian, record, "-5")


class LifecycleTests(Setup):
    def test_propose_approve_execute_retires_the_item(self):
        proposal = LifecycleService.propose(self.custodian, self.chair, K.DONATION, "surplus, still good")
        self.assertFalse(Asset.objects.get(pk=self.chair.pk).is_listed)
        self.assertTrue(Notification.objects.filter(user=self.approver, message__contains="donation").exists())
        LifecycleService.decide(self.approver, proposal, True)
        with self.assertRaisesMessage(MaintenanceError, "evidence"):
            LifecycleService.execute(self.custodian, proposal, "")
        LifecycleService.execute(self.custodian, proposal, "Charity receipt 1234")
        self.assertEqual(self.status(proposal), L.EXECUTED)
        self.assertEqual(self.status(self.chair), A.RETIRED)

    def test_proposer_cannot_approve_own_proposal(self):
        both = with_role(make_user(department=self.it), "Custodian", "Approver")
        proposal = LifecycleService.propose(both, self.chair, K.RECYCLING, "broken beyond repair")
        with self.assertRaisesMessage(MaintenanceError, "BR-02"):
            LifecycleService.decide(both, proposal, True)

    def test_reject_needs_a_reason_and_keeps_the_item(self):
        proposal = LifecycleService.propose(self.custodian, self.chair, K.DISPOSAL, "old")
        with self.assertRaises(MaintenanceError):
            LifecycleService.decide(self.approver, proposal, False, "")
        LifecycleService.decide(self.approver, proposal, False, "can still be reused")
        self.assertEqual(self.status(proposal), L.REJECTED)
        self.assertEqual(self.status(self.chair), A.AVAILABLE)

    def test_one_open_proposal_per_item(self):
        LifecycleService.propose(self.custodian, self.chair, K.DONATION, "surplus")
        with self.assertRaisesMessage(MaintenanceError, "open proposal"):
            LifecycleService.propose(self.custodian, self.chair, K.RECYCLING, "surplus")


class PageTests(Setup):
    def test_requester_reports_from_the_page_but_cannot_repair(self):
        self.client.login(email=self.requester.email, password=PASSWORD)
        self.assertEqual(self.client.get(reverse("maintenance:list")).status_code, 200)
        self.client.post(reverse("maintenance:report"), {"asset": self.chair.pk, "description": "seat torn"})
        record = self.chair.maintenance_records.get()
        self.assertEqual(self.client.post(reverse("maintenance:start", args=[record.pk])).status_code, 403)

    def test_custodian_and_approver_pages(self):
        record = MaintenanceService.report_fault(self.requester, self.chair, "seat torn")
        self.client.login(email=self.custodian.email, password=PASSWORD)
        self.assertContains(self.client.get(reverse("maintenance:list")), "seat torn")
        self.client.post(reverse("maintenance:start", args=[record.pk]))
        self.assertEqual(self.status(self.chair), A.UNDER_MAINTENANCE)
        self.assertContains(self.client.get(reverse("assets:detail", args=[self.chair.pk])), "Open fault")

        proposal = LifecycleService.propose(self.custodian, self.chair, K.RECYCLING, "frame cracked")
        self.client.login(email=self.approver.email, password=PASSWORD)
        self.assertContains(self.client.get(reverse("maintenance:list")), "frame cracked")
        self.client.post(reverse("maintenance:decide", args=[proposal.pk]), {"decision": "approve"})
        self.assertEqual(self.status(proposal), L.APPROVED)
