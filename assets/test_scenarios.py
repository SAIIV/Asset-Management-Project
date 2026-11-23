"""Scenarios across features: faults and retirement meeting requests, transfers, the catalogue and the
asset page. Each test is one situation that used to leave an item stuck or allowed a clash."""

from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, UserRole
from assets.maintenance import LifecycleService, MaintenanceError, MaintenanceService
from assets.models import Asset
from circular_campus.choices import (
    ApprovalDecision as D,
    AssetStatus as A,
    LifecycleActionType as K,
    MaintenanceStatus as M,
    RequestStatus as R,
    ReservationStatus as V,
    TransferStatus as T,
)
from circular_campus.test_utils import make_asset, make_department, make_user
from exchange.catalogue import CatalogueError, CatalogueService
from exchange.requests import RequestService
from notifications.models import Notification
from transfers.models import Approval, Reservation, Transfer
from transfers.services import TransferError, TransferService

PASSWORD = "Test-pass-123"


def with_role(user, *names):
    for name in names:
        UserRole.objects.create(user=user, role=Role.objects.get_or_create(name=name)[0])
    return user


class Scenario(TestCase):
    def setUp(self):
        self.it, self.chem = make_department(name="IT"), make_department(name="Chemistry")
        self.custodian = with_role(make_user(department=self.it), "Custodian")
        self.requester = with_role(make_user(department=self.chem), "Requester")
        self.approver = with_role(make_user(department=self.chem), "Approver")
        self.scope = make_asset(name="Microscope", owner_department=self.it, status=A.AVAILABLE, is_listed=True,
                                description="student microscope", campus="Main", building="B1", room="101")
        self.request = RequestService.create(self.requester, {
            "purpose": "Lab class", "quantity": 1, "required_by": date.today() + timedelta(days=7),
            "urgency": "Normal", "type": "Permanent", "mandatory_specs": [], "preferred_condition": "",
            "candidates": [self.scope],
        })

    def get(self, obj):
        return type(obj).objects.get(pk=obj.pk)

    def reserve(self):
        TransferService.reserve(self.custodian, self.request, [self.scope])


class FaultWhileReserved(Scenario):
    def test_repair_frees_the_request_under_review(self):
        self.reserve()
        record = MaintenanceService.report_fault(self.custodian, self.scope, "lamp dead")
        MaintenanceService.start_repair(self.custodian, record)
        self.assertEqual(self.get(self.scope).status, A.UNDER_MAINTENANCE)
        self.assertEqual(self.get(self.request).status, R.SUBMITTED)
        self.assertEqual(Reservation.objects.get().status, V.RELEASED)
        self.assertTrue(Notification.objects.filter(user=self.requester, message__contains="went for repair").exists())
        MaintenanceService.finish_repair(self.custodian, record)
        self.assertEqual(self.get(self.scope).status, A.AVAILABLE)  # back with its owner, not reserved

    def test_repair_after_approval_cancels_the_transfer(self):
        self.reserve()
        TransferService.decide(self.approver, self.request, D.APPROVED, "ok")
        record = MaintenanceService.report_fault(self.custodian, self.scope, "lamp dead")
        MaintenanceService.start_repair(self.custodian, record)
        self.assertEqual(Transfer.objects.get().status, T.CANCELLED)
        self.assertEqual(Approval.objects.get().decision, D.INVALIDATED)
        self.assertEqual(self.get(self.request).status, R.SUBMITTED)
        self.assertTrue(Notification.objects.filter(user=self.approver, message__contains="no longer applies").exists())

    def test_repair_waits_once_dispatched(self):
        self.reserve()
        TransferService.decide(self.approver, self.request, D.APPROVED, "ok")
        TransferService.release(self.custodian, Transfer.objects.get())
        record = MaintenanceService.report_fault(self.requester, self.scope, "arrived cracked")
        with self.assertRaisesMessage(MaintenanceError, "on its way"):
            MaintenanceService.start_repair(self.custodian, record)
        TransferService.receive(self.requester, Transfer.objects.get(), "Fair")
        receiving = with_role(make_user(department=self.chem), "Custodian")
        MaintenanceService.start_repair(receiving, record)  # the new owner repairs it
        self.assertEqual(self.get(self.scope).status, A.UNDER_MAINTENANCE)
        MaintenanceService.finish_repair(receiving, record)
        self.assertEqual(self.get(self.scope).status, A.IN_USE)


class Holds(Scenario):
    def test_fault_report_takes_item_off_catalogue_and_closing_puts_it_back(self):
        record = MaintenanceService.report_fault(self.requester, self.scope, "focus stuck")
        self.assertFalse(self.get(self.scope).is_listed)
        MaintenanceService.cancel(self.custodian, record, "no fault found")
        self.assertTrue(self.get(self.scope).is_listed)

    def test_open_fault_blocks_reserve_and_publish(self):
        MaintenanceService.report_fault(self.requester, self.scope, "focus stuck")
        with self.assertRaisesMessage(TransferError, "open fault"):
            self.reserve()
        with self.assertRaisesMessage(CatalogueError, "open fault"):
            CatalogueService.publish(self.custodian, self.scope)

    def test_open_proposal_blocks_reserve_and_reserve_page_hides_it(self):
        LifecycleService.propose(self.custodian, self.scope, K.DONATION, "surplus")
        with self.assertRaisesMessage(TransferError, "proposed"):
            self.reserve()
        self.client.login(email=self.custodian.email, password=PASSWORD)
        page = self.client.get(reverse("transfers:custodian_request", args=[self.request.pk]))
        self.assertNotIn(self.scope.pk, [a.pk for a in page.context["units"]])

    def test_report_from_catalogue_page_does_not_land_on_a_404(self):
        self.client.login(email=self.requester.email, password=PASSWORD)
        back = reverse("exchange:catalogue_detail", args=[self.scope.pk])
        response = self.client.post(reverse("maintenance:report"),
                                    {"asset": self.scope.pk, "description": "eyepiece missing", "next": back})
        self.assertEqual(response["Location"], reverse("maintenance:list"))


class RetireAndRepair(Scenario):
    def test_retiring_an_item_under_repair_closes_the_fault(self):
        record = MaintenanceService.report_fault(self.custodian, self.scope, "motor burnt")
        MaintenanceService.start_repair(self.custodian, record)
        proposal = LifecycleService.propose(self.custodian, self.scope, K.RECYCLING, "beyond repair")
        LifecycleService.decide(self.approver, proposal, True)
        LifecycleService.execute(self.custodian, proposal, "Recycler note 77")
        self.assertEqual(self.get(self.scope).status, A.RETIRED)
        self.assertEqual(self.get(record).status, M.CANCELLED)

    def test_manual_status_change_refused_during_repair(self):
        record = MaintenanceService.report_fault(self.custodian, self.scope, "motor burnt")
        MaintenanceService.start_repair(self.custodian, record)
        self.client.login(email=self.custodian.email, password=PASSWORD)
        self.client.post(reverse("assets:move", args=[self.scope.pk]), {"status": A.AVAILABLE, "reason": "x"})
        self.assertEqual(self.get(self.scope).status, A.UNDER_MAINTENANCE)

    def test_repair_of_item_moved_by_hand(self):
        record = MaintenanceService.report_fault(self.custodian, self.scope, "motor burnt")
        Asset.objects.filter(pk=self.scope.pk).update(status=A.UNDER_MAINTENANCE)
        MaintenanceService.start_repair(self.custodian, record)
        MaintenanceService.finish_repair(self.custodian, record)
        self.assertEqual(self.get(self.scope).status, A.AVAILABLE)
