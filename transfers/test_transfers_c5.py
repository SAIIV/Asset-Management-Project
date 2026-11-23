"""C5 Approve and transfer: reserve, independent approval, release, receipt and custody change."""

from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, UserRole
from assets.models import Asset
from circular_campus.choices import (
    ApprovalDecision as D,
    AssetStatus as A,
    RequestStatus as R,
    ReservationStatus as V,
    TransferStatus as T,
)
from circular_campus.test_utils import make_asset, make_department, make_user
from exchange.models import ResourceRequest
from exchange.requests import RequestService
from notifications.models import Notification
from transfers.models import Approval, Reservation, Transfer
from transfers.services import TransferError, TransferService

PASSWORD = "Test-pass-123"


def with_role(user, name):
    UserRole.objects.create(user=user, role=Role.objects.get_or_create(name=name)[0])
    return user


class Flow(TestCase):
    def setUp(self):
        self.chem, self.it = make_department(name="Chemistry"), make_department(name="IT Services")
        self.requester = with_role(make_user(department=self.chem), "Requester")
        self.custodian = with_role(make_user(department=self.it), "Custodian")
        self.approver = with_role(make_user(department=self.it), "Approver")
        self.monitor = make_asset(name="Dell monitor", owner_department=self.it, status=A.AVAILABLE, is_listed=True)
        self.request = RequestService.create(self.requester, {
            "purpose": "Lab screens", "quantity": 1, "required_by": date.today() + timedelta(days=7),
            "urgency": "Normal", "type": "Permanent", "mandatory_specs": [], "preferred_condition": "",
            "candidates": [self.monitor],
        })

    def status(self, obj):
        return type(obj).objects.get(pk=obj.pk).status

    def reserve(self):
        return TransferService.reserve(self.custodian, self.request, [self.monitor])

    def approve(self):
        self.reserve()
        return TransferService.decide(self.approver, self.request, D.APPROVED, "ok")


class ServiceTests(Flow):
    def test_full_flow_moves_custody_only_on_receipt(self):
        self.reserve()
        self.assertEqual(self.status(self.request), R.UNDER_REVIEW)
        self.assertEqual(self.status(self.monitor), A.RESERVED)
        self.assertTrue(Notification.objects.filter(user=self.approver, message__contains="waiting for approval").exists())

        TransferService.decide(self.approver, self.request, D.APPROVED, "fits the lab")
        transfer = Transfer.objects.get()
        self.assertEqual((transfer.status, self.status(self.request)), (T.SCHEDULED, R.APPROVED))

        TransferService.release(self.custodian, transfer)
        self.assertEqual(self.status(transfer), T.DISPATCHED)
        self.assertEqual(self.status(self.monitor), A.IN_TRANSIT)
        self.assertEqual(Asset.objects.get(pk=self.monitor.pk).owner_department, self.it)  # custody unchanged
        self.assertEqual(Reservation.objects.get().status, V.CONSUMED)

        TransferService.receive(self.requester, transfer, "Good")
        asset = Asset.objects.get(pk=self.monitor.pk)
        self.assertEqual((asset.status, asset.owner_department), (A.IN_USE, self.chem))
        self.assertFalse(asset.is_listed)
        self.assertEqual(self.status(transfer), T.RECEIVED)
        self.assertEqual(self.status(self.request), R.FULFILLED)

    def test_no_self_approval(self):
        self_approver = with_role(self.requester, "Approver")
        self.reserve()
        with self.assertRaises(TransferError):
            TransferService.decide(self_approver, self.request, D.APPROVED)
        self.assertEqual(self.status(self.request), R.UNDER_REVIEW)
        self.assertFalse(Approval.objects.exists())

    def test_last_unit_cannot_go_to_two_requests(self):
        self.reserve()
        other = RequestService.create(with_role(make_user(department=self.chem), "Requester"), {
            "purpose": "Me too", "quantity": 1, "required_by": date.today() + timedelta(days=7),
            "urgency": "Normal", "type": "Permanent", "mandatory_specs": [], "preferred_condition": "",
            "candidates": [],
        })
        with self.assertRaises(TransferError):
            TransferService.reserve(self.custodian, other, [self.monitor])
        self.assertEqual(Reservation.objects.filter(asset=self.monitor, status=V.ACTIVE).count(), 1)

    def test_reserve_is_all_or_nothing(self):
        broken = make_asset(owner_department=self.it, status=A.UNDER_MAINTENANCE)
        ResourceRequest.objects.filter(pk=self.request.pk).update(quantity=2)
        with self.assertRaises(TransferError):
            TransferService.reserve(self.custodian, self.request, [self.monitor, broken])
        self.assertFalse(Reservation.objects.exists())
        self.assertEqual(self.status(self.monitor), A.AVAILABLE)

    def test_cannot_reserve_another_departments_asset(self):
        theirs = make_asset(owner_department=self.chem, status=A.AVAILABLE)
        with self.assertRaises(TransferError):
            TransferService.reserve(self.custodian, self.request, [theirs])

    def test_reject_needs_reason_and_releases_units(self):
        self.reserve()
        with self.assertRaises(TransferError):
            TransferService.decide(self.approver, self.request, D.REJECTED, "")
        TransferService.decide(self.approver, self.request, D.REJECTED, "budget")
        self.assertEqual(self.status(self.request), R.REJECTED)
        self.assertEqual(self.status(self.monitor), A.AVAILABLE)
        self.assertEqual(Reservation.objects.get().status, V.RELEASED)
        self.assertTrue(Notification.objects.filter(user=self.requester, message__contains="budget").exists())

    def test_return_for_correction_goes_back_to_submitted(self):
        self.reserve()
        TransferService.decide(self.approver, self.request, D.RETURNED_FOR_CORRECTION, "say which lab")
        self.assertEqual(self.status(self.request), R.SUBMITTED)
        self.assertEqual(self.status(self.monitor), A.AVAILABLE)

    def test_dispute_keeps_custody_then_resolution_moves_it(self):
        self.approve()
        transfer = Transfer.objects.get()
        TransferService.release(self.custodian, transfer)
        TransferService.receive(self.requester, transfer, "Fair", all_ok=False, note="scratched screen")
        self.assertEqual(self.status(transfer), T.DISPUTED)
        self.assertEqual(Asset.objects.get(pk=self.monitor.pk).owner_department, self.it)
        TransferService.receive(self.requester, transfer, "Fair", note="accepted as is")
        self.assertEqual(Asset.objects.get(pk=self.monitor.pk).owner_department, self.chem)
        self.assertEqual(Transfer.objects.get().condition_on_receipt, "Fair")

    def test_only_requester_confirms_receipt(self):
        self.approve()
        transfer = Transfer.objects.get()
        TransferService.release(self.custodian, transfer)
        with self.assertRaises(TransferError):
            TransferService.receive(self.custodian, transfer, "Good")

    def test_cannot_release_twice(self):
        self.approve()
        transfer = Transfer.objects.get()
        TransferService.release(self.custodian, transfer)
        with self.assertRaises(TransferError):
            TransferService.release(self.custodian, transfer)


class PageTests(Flow):
    def login(self, user):
        self.client.login(email=user.email, password=PASSWORD)

    def test_demo_path_through_the_pages(self):
        self.login(self.custodian)
        self.assertContains(self.client.get(reverse("transfers:incoming")), f"#{self.request.pk}")
        self.client.post(reverse("transfers:custodian_request", args=[self.request.pk]), {"assets": [self.monitor.pk]})
        self.assertEqual(self.status(self.request), R.UNDER_REVIEW)

        self.login(self.approver)
        self.assertContains(self.client.get(reverse("transfers:approvals")), f"#{self.request.pk}")
        self.client.post(reverse("transfers:approval_detail", args=[self.request.pk]),
                         {"decision": "Approved", "reason": "ok"})
        transfer = Transfer.objects.get()

        self.login(self.custodian)
        self.client.post(reverse("transfers:release", args=[transfer.pk]))
        self.assertEqual(self.status(transfer), T.DISPATCHED)

        self.login(self.requester)
        page = self.client.get(reverse("exchange:request_detail", args=[self.request.pk]))
        self.assertContains(page, reverse("transfers:receive", args=[transfer.pk]))
        self.client.post(reverse("transfers:receive", args=[transfer.pk]), {"condition": "Good", "outcome": "ok"})
        self.assertEqual(self.status(self.request), R.FULFILLED)

    def test_approver_cannot_open_own_request(self):
        self_approver = with_role(self.requester, "Approver")
        self.reserve()
        self.login(self_approver)
        self.assertEqual(self.client.get(reverse("transfers:approval_detail", args=[self.request.pk])).status_code, 403)
        self.assertNotContains(self.client.get(reverse("transfers:approvals")), f"#{self.request.pk}<")

    def test_other_department_custodian_cannot_release(self):
        self.approve()
        transfer = Transfer.objects.get()
        stranger = with_role(make_user(department=self.chem), "Custodian")
        self.login(stranger)
        self.assertEqual(self.client.post(reverse("transfers:release", args=[transfer.pk])).status_code, 403)
        self.assertEqual(self.status(transfer), T.SCHEDULED)

    def test_other_requester_cannot_confirm(self):
        self.approve()
        transfer = Transfer.objects.get()
        TransferService.release(self.custodian, transfer)
        stranger = with_role(make_user(department=self.chem), "Requester")
        self.login(stranger)
        response = self.client.post(reverse("transfers:receive", args=[transfer.pk]), {"condition": "Good"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.status(transfer), T.DISPATCHED)

    def test_requester_cannot_open_approvals_or_incoming(self):
        self.login(self.requester)
        self.assertEqual(self.client.get(reverse("transfers:approvals")).status_code, 403)
        self.assertEqual(self.client.get(reverse("transfers:incoming")).status_code, 403)

    def test_inbox_link_sends_each_role_to_its_page(self):
        self.reserve()
        self.login(self.approver)
        response = self.client.get(reverse("transfers:open_request", args=[self.request.pk]))
        self.assertRedirects(response, reverse("transfers:approval_detail", args=[self.request.pk]))
        self.login(self.custodian)
        response = self.client.get(reverse("transfers:open_request", args=[self.request.pk]))
        self.assertRedirects(response, reverse("transfers:custodian_request", args=[self.request.pk]))

    def test_inbox_link_still_opens_for_the_approver_after_the_request_moved_on(self):
        self.approve()
        transfer = Transfer.objects.get()
        TransferService.release(self.custodian, transfer)
        TransferService.receive(self.requester, transfer, "Good")
        self.login(self.approver)
        response = self.client.get(reverse("transfers:open_request", args=[self.request.pk]))
        self.assertRedirects(response, reverse("transfers:approval_detail", args=[self.request.pk]))
        page = self.client.get(reverse("transfers:approval_detail", args=[self.request.pk]))
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, 'name="decision"')
