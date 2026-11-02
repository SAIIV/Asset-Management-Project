"""Tests for Reservation, Approval and Transfer."""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from assets.models import LifecycleAction
from circular_campus.test_utils import make_asset, make_request, make_user, now
from transfers.models import Approval, Reservation, Transfer


class ReservationTests(TestCase):
    def test_only_one_active_reservation_per_asset(self):
        asset = make_asset()
        first = Reservation.objects.create(request=make_request(), asset=asset)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Reservation.objects.create(request=make_request(), asset=asset)
        # Once the first one is released, the asset can be reserved again.
        first.status = "Released"
        first.released_at = now()
        first.save()
        Reservation.objects.create(request=make_request(), asset=asset)
        self.assertEqual(Reservation.objects.filter(asset=asset).count(), 2)


class ApprovalTests(TestCase):
    def test_exactly_one_target(self):
        approver = make_user()
        request = make_request()
        action = LifecycleAction.objects.create(asset=make_asset(), action="Donation", reason="surplus")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Approval.objects.create(approver=approver)  # no target
        with self.assertRaises(IntegrityError), transaction.atomic():
            Approval.objects.create(approver=approver, request=request, lifecycle_action=action)  # two targets
        Approval.objects.create(approver=approver, request=request)
        Approval.objects.create(approver=approver, lifecycle_action=action)

    def test_approver_cannot_be_the_requester(self):
        requester = make_user()
        approval = Approval(approver=requester, request=make_request(requester=requester))
        with self.assertRaises(ValidationError):
            approval.clean()
        Approval(approver=make_user(), request=approval.request).clean()  # another person is fine

    def test_decision_starts_pending_and_only_accepts_enum_values(self):
        approval = Approval.objects.create(approver=make_user(), request=make_request())
        self.assertEqual(approval.decision, "Pending")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Approval.objects.filter(pk=approval.pk).update(decision="Maybe")


class TransferTests(TestCase):
    def test_asset_request_and_approver_are_required(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Transfer.objects.create(asset=make_asset(), request=make_request(), approver_id=None)

    def test_received_needs_receipt_time(self):
        fields = {"asset": make_asset(), "request": make_request(), "approver": make_user()}
        with self.assertRaises(IntegrityError), transaction.atomic():
            Transfer.objects.create(status="Received", **fields)
        Transfer.objects.create(status="Received", received_at=now(), condition_on_receipt="Good", **fields)
