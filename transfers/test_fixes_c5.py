"""Fixes from testing (19 Nov): "Cannot supply" for custodians (UC-13 alternative) and Review buttons."""

from django.urls import reverse

from accounts.models import AuditLog
from circular_campus.choices import AssetStatus as A, RequestStatus as R
from circular_campus.test_utils import make_asset
from notifications.models import Notification
from transfers.services import TransferError, TransferService
from transfers.test_transfers_c5 import PASSWORD, Flow


class CannotSupplyTests(Flow):
    def test_request_stays_open_and_requester_is_told(self):
        TransferService.cannot_supply(self.custodian, self.request, "Our only spare monitor is broken")
        self.assertEqual(self.status(self.request), R.SUBMITTED)  # not rejected: only an approver rejects
        self.assertEqual(self.status(self.monitor), A.AVAILABLE)
        message = Notification.objects.filter(user=self.requester).latest("id").message
        self.assertIn("cannot supply request", message)
        self.assertIn("Our only spare monitor is broken", message)
        self.assertEqual(AuditLog.objects.get(action="cannot_supply").reason, "Our only spare monitor is broken")

    def test_reason_is_required_and_only_while_submitted(self):
        with self.assertRaises(TransferError):
            TransferService.cannot_supply(self.custodian, self.request, "  ")
        self.reserve()
        with self.assertRaises(TransferError):
            TransferService.cannot_supply(self.custodian, self.request, "too late")

    def test_from_the_request_page(self):
        self.client.login(email=self.custodian.email, password=PASSWORD)
        page = self.client.get(reverse("transfers:custodian_request", args=[self.request.pk]))
        self.assertContains(page, "Cannot supply it?")
        response = self.client.post(reverse("transfers:cannot_supply", args=[self.request.pk]),
                                    {"reason": "Nothing suitable"}, follow=True)
        self.assertContains(response, "You said: cannot supply")
        self.client.login(email=self.requester.email, password=PASSWORD)
        self.assertEqual(self.client.post(reverse("transfers:cannot_supply", args=[self.request.pk]),
                                          {"reason": "x"}).status_code, 403)


class ReviewButtonTests(Flow):
    def test_incoming_and_approvals_have_review_buttons(self):
        self.client.login(email=self.custodian.email, password=PASSWORD)
        url = reverse("transfers:custodian_request", args=[self.request.pk])
        self.assertContains(self.client.get(reverse("transfers:incoming")), f'class="btn primary" href="{url}">Review')
        self.reserve()
        self.client.login(email=self.approver.email, password=PASSWORD)
        url = reverse("transfers:approval_detail", args=[self.request.pk])
        self.assertContains(self.client.get(reverse("transfers:approvals")), f'class="btn primary" href="{url}">Review')

    def test_requesters_choice_is_listed_first(self):
        make_asset(name="Newer unit", owner_department=self.it, status=A.AVAILABLE)
        self.client.login(email=self.custodian.email, password=PASSWORD)
        units = self.client.get(reverse("transfers:custodian_request", args=[self.request.pk])).context["units"]
        self.assertEqual(units[0], self.monitor)
