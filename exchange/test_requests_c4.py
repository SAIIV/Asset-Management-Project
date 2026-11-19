"""C4 Request and track: submit, revise, cancel and follow your own requests."""

from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from accounts.models import AuditLog, Role, UserRole
from assets.models import Asset
from circular_campus.choices import AssetStatus as A, RequestStatus as R
from circular_campus.test_utils import make_asset, make_department, make_user
from exchange.models import ResourceRequest
from exchange.requests import RequestError, RequestService, candidates_of
from notifications.models import Notification
from transfers.models import Reservation

PASSWORD = "Test-pass-123"
NEXT_WEEK = date.today() + timedelta(days=7)


def with_role(user, name):
    UserRole.objects.create(user=user, role=Role.objects.get_or_create(name=name)[0])
    return user


def data(**overrides):
    values = {"purpose": "Second screens for the teaching lab", "quantity": 1, "required_by": NEXT_WEEK,
              "urgency": "Normal", "type": "Permanent", "mandatory_specs": ["HDMI"],
              "preferred_condition": "", "candidates": []}
    values.update(overrides)
    return values


class Base(TestCase):
    def setUp(self):
        self.chem, self.it = make_department(name="Chemistry"), make_department(name="IT Services")
        self.requester = with_role(make_user(department=self.chem), "Requester")
        self.custodian = with_role(make_user(department=self.it), "Custodian")
        self.monitor = make_asset(name="Dell monitor", owner_department=self.it, status=A.AVAILABLE, is_listed=True)


class RequestServiceTests(Base):
    def test_submit_creates_submitted_request_with_history_and_messages(self):
        req = RequestService.create(self.requester, data(candidates=[self.monitor]))
        self.assertEqual(req.status, R.SUBMITTED)
        self.assertEqual(candidates_of(req), [self.monitor])
        self.assertEqual(req.specification.mandatory_specs, ["HDMI"])
        actions = set(AuditLog.objects.filter(record_type="ResourceRequest", record_id=req.pk)
                      .values_list("action", flat=True))
        self.assertEqual(actions, {"create_request", "submit_request"})
        self.assertTrue(Notification.objects.filter(user=self.requester).exists())
        self.assertTrue(Notification.objects.filter(user=self.custodian, message__contains="Dell monitor").exists())

    def test_save_as_draft(self):
        req = RequestService.create(self.requester, data(), submit=False)
        self.assertEqual(req.status, R.DRAFT)
        RequestService.submit(self.requester, req)
        self.assertEqual(ResourceRequest.objects.get(pk=req.pk).status, R.SUBMITTED)

    def test_past_date_is_refused_on_submit(self):
        with self.assertRaises(RequestError):
            RequestService.create(self.requester, data(required_by=date.today() - timedelta(days=1)))
        self.assertFalse(ResourceRequest.objects.exists())

    def test_more_candidates_than_quantity_is_refused(self):
        other = make_asset(owner_department=self.it, status=A.AVAILABLE, is_listed=True)
        with self.assertRaises(RequestError):
            RequestService.create(self.requester, data(quantity=1, candidates=[self.monitor, other]))

    def test_unlisted_or_own_department_candidate_is_refused(self):
        hidden = make_asset(owner_department=self.it, status=A.AVAILABLE, is_listed=False)
        own = make_asset(owner_department=self.chem, status=A.AVAILABLE, is_listed=True)
        for asset in (hidden, own):
            with self.assertRaises(RequestError):
                RequestService.create(self.requester, data(candidates=[asset]))

    def test_revise_submitted_request(self):
        req = RequestService.create(self.requester, data())
        RequestService.revise(self.requester, req, data(quantity=2, purpose="Changed"))
        req.refresh_from_db()
        self.assertEqual((req.quantity, req.specification.purpose, req.status), (2, "Changed", R.SUBMITTED))
        self.assertTrue(AuditLog.objects.filter(action="revise_request", record_id=req.pk).exists())

    def test_cannot_revise_once_units_are_reserved(self):
        req = RequestService.create(self.requester, data(candidates=[self.monitor]))
        Reservation.objects.create(request=req, asset=self.monitor)
        with self.assertRaises(RequestError):
            RequestService.revise(self.requester, req, data(quantity=3))

    def test_cancel_releases_reserved_units(self):
        req = RequestService.create(self.requester, data(candidates=[self.monitor]))
        Asset.objects.filter(pk=self.monitor.pk).update(status=A.RESERVED)
        reservation = Reservation.objects.create(request=req, asset=self.monitor)
        RequestService.cancel(self.requester, req, reason="no longer needed")
        self.assertEqual(ResourceRequest.objects.get(pk=req.pk).status, R.CANCELLED)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, "Released")
        self.assertIsNotNone(reservation.released_at)
        self.assertEqual(Asset.objects.get(pk=self.monitor.pk).status, A.AVAILABLE)

    def test_cannot_cancel_twice(self):
        req = RequestService.create(self.requester, data())
        RequestService.cancel(self.requester, req)
        with self.assertRaises(RequestError):
            RequestService.cancel(self.requester, req)


class RequestPageTests(Base):
    def setUp(self):
        super().setUp()
        self.client.login(email=self.requester.email, password=PASSWORD)

    def form(self, **overrides):
        values = {"purpose": "Screens", "quantity": "1", "required_by": NEXT_WEEK.isoformat(),
                  "urgency": "Normal", "type": "Permanent", "mandatory_specs_text": "HDMI, 22 inch",
                  "preferred_condition": "", "submit": "1"}
        values.update(overrides)
        return values

    def test_submit_from_form_and_see_it_in_my_requests(self):
        response = self.client.post(reverse("exchange:request_create"),
                                    self.form(candidates=[self.monitor.pk]))
        req = ResourceRequest.objects.get()
        self.assertRedirects(response, reverse("exchange:request_detail", args=[req.pk]))
        self.assertEqual(req.specification.mandatory_specs, ["HDMI", "22 inch"])
        page = self.client.get(reverse("exchange:requests"))
        self.assertContains(page, f"#{req.pk}")
        self.assertContains(page, "Submitted")

    def test_save_draft_button(self):
        data_ = self.form()
        data_.pop("submit")
        data_["save_draft"] = "1"
        self.client.post(reverse("exchange:request_create"), data_)
        self.assertEqual(ResourceRequest.objects.get().status, R.DRAFT)

    def test_form_errors_keep_entries(self):
        response = self.client.post(reverse("exchange:request_create"),
                                    self.form(required_by=(date.today() - timedelta(days=2)).isoformat()))
        self.assertContains(response, "cannot be in the past")
        self.assertContains(response, "Screens")
        self.assertFalse(ResourceRequest.objects.exists())

    def test_request_this_item_pre_ticks_the_asset(self):
        detail = self.client.get(reverse("exchange:catalogue_detail", args=[self.monitor.pk]))
        self.assertContains(detail, f"?asset={self.monitor.pk}")
        form = self.client.get(reverse("exchange:request_create"), {"asset": self.monitor.pk})
        self.assertEqual(form.context["form"].initial["candidates"], [self.monitor.pk])


    def test_other_requesters_request_is_403(self):
        other = with_role(make_user(department=self.chem), "Requester")
        theirs = RequestService.create(other, data())
        self.assertEqual(self.client.get(reverse("exchange:request_detail", args=[theirs.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("exchange:request_cancel", args=[theirs.pk])).status_code, 403)
        self.assertEqual(ResourceRequest.objects.get(pk=theirs.pk).status, R.SUBMITTED)

    def test_custodian_cannot_make_requests(self):
        self.client.login(email=self.custodian.email, password=PASSWORD)
        self.assertEqual(self.client.get(reverse("exchange:request_create")).status_code, 403)

    def test_cancel_from_page(self):
        req = RequestService.create(self.requester, data())
        self.client.post(reverse("exchange:request_cancel", args=[req.pk]), {"reason": "changed plans"})
        self.assertEqual(ResourceRequest.objects.get(pk=req.pk).status, R.CANCELLED)
        page = self.client.get(reverse("exchange:request_detail", args=[req.pk]))
        self.assertContains(page, "changed plans")

    def test_notification_opens_the_request(self):
        req = RequestService.create(self.requester, data())
        note = Notification.objects.get(user=self.requester)
        response = self.client.post(reverse("notifications:open", args=[note.pk]), follow=True)
        self.assertEqual(response.redirect_chain[-1][0], reverse("exchange:request_detail", args=[req.pk]))

