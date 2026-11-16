"""C6 States and history: only the arrows of the state diagrams are allowed, and every move is recorded."""

from django.test import TestCase
from django.urls import reverse

from accounts.models import AuditLog, Role, UserRole
from assets.models import Asset, ITAsset
from assets.states import (
    ASSET_MOVES,
    IllegalMove,
    StateService,
    allowed_moves,
    custodian_moves,
    history_of,
    is_allowed,
)
from circular_campus.choices import AssetStatus as A, RequestStatus as R, TransferStatus as T
from circular_campus.test_utils import make_asset, make_department, make_request, make_user

PASSWORD = "Test-pass-123"


def with_role(user, name):
    UserRole.objects.create(user=user, role=Role.objects.get_or_create(name=name)[0])
    return user


class StateDiagramTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_every_asset_state_appears_in_the_diagram(self):
        used = {state for move in ASSET_MOVES for state in move}
        self.assertEqual(used, set(A.values))

    def test_allowed_move_changes_status_and_writes_history(self):
        asset = make_asset(status=A.DRAFT)
        StateService.move(self.user, asset, A.AVAILABLE, reason="checked")
        asset.refresh_from_db()
        self.assertEqual(asset.status, A.AVAILABLE)
        event = history_of("Asset", asset.pk).first()
        self.assertEqual(event.user, self.user)
        self.assertEqual(event.before_value, {"status": "Draft"})
        self.assertEqual(event.after_value, {"status": "Available"})
        self.assertEqual(event.reason, "checked")

    def test_move_not_in_diagram_is_refused_and_nothing_changes(self):
        asset = make_asset(status=A.DRAFT)
        with self.assertRaises(IllegalMove):
            StateService.move(self.user, asset, A.IN_USE)  # no arrow Draft -> InUse
        asset.refresh_from_db()
        self.assertEqual(asset.status, A.DRAFT)
        self.assertFalse(AuditLog.objects.filter(record_type="Asset", record_id=asset.pk).exists())

    def test_retired_is_terminal(self):
        asset = make_asset(status=A.RETIRED)
        self.assertEqual(allowed_moves(asset), {})
        for state in A.values:
            with self.assertRaises(IllegalMove):
                StateService.move(self.user, asset, state)

    def test_custody_moves_only_through_in_transit(self):
        # Available -> InUse directly would skip release and receipt (BR-07).
        self.assertFalse(is_allowed("Asset", A.AVAILABLE, A.IN_USE))
        self.assertTrue(is_allowed("Asset", A.RESERVED, A.IN_TRANSIT))
        self.assertTrue(is_allowed("Asset", A.IN_TRANSIT, A.IN_USE))

    def test_move_bumps_version_so_an_open_edit_form_is_refused(self):
        asset = make_asset(status=A.AVAILABLE)
        StateService.move(self.user, asset, A.UNDER_MAINTENANCE)
        self.assertEqual(Asset.objects.get(pk=asset.pk).version, 2)

    def test_leaving_the_catalogue_unlists_the_asset(self):
        asset = make_asset(status=A.AVAILABLE, is_listed=True)
        StateService.move(self.user, asset, A.UNDER_MAINTENANCE)
        self.assertFalse(Asset.objects.get(pk=asset.pk).is_listed)

    def test_subtype_asset_uses_the_asset_diagram(self):
        laptop = make_asset(model=ITAsset, serial_number="SN-C6-1", status=A.AVAILABLE)
        StateService.move(self.user, laptop, A.RESERVED)
        self.assertEqual(Asset.objects.get(pk=laptop.pk).status, A.RESERVED)
        self.assertTrue(history_of("Asset", laptop.pk).exists())

    def test_request_diagram(self):
        request = make_request(status=R.DRAFT)
        StateService.move(self.user, request, R.SUBMITTED)
        with self.assertRaises(IllegalMove):
            StateService.move(self.user, request, R.APPROVED)  # must be reviewed first
        with self.assertRaises(IllegalMove):
            StateService.move(self.user, request, R.FULFILLED)

    def test_transfer_diagram(self):
        self.assertTrue(is_allowed("Transfer", T.DISPATCHED, T.DISPUTED))
        self.assertTrue(is_allowed("Transfer", T.DISPUTED, T.RECEIVED))
        self.assertFalse(is_allowed("Transfer", T.DISPATCHED, T.CANCELLED))  # too late to cancel

    def test_custodian_page_offers_only_manual_moves(self):
        reserved = make_asset(status=A.RESERVED)
        self.assertEqual(custodian_moves(reserved), {})  # release/cancel belong to C5
        draft = make_asset(status=A.DRAFT)
        self.assertEqual(set(custodian_moves(draft)), {A.AVAILABLE})


class StatusPageTests(TestCase):
    def setUp(self):
        self.dept, self.other_dept = make_department(), make_department()
        self.custodian = with_role(make_user(department=self.dept), "Custodian")
        self.client.login(email=self.custodian.email, password=PASSWORD)

    def post_move(self, asset, status, reason=""):
        return self.client.post(reverse("assets:move", args=[asset.pk]), {"status": status, "reason": reason})

    def test_custodian_moves_asset_and_sees_it_in_history(self):
        asset = make_asset(owner_department=self.dept, status=A.AVAILABLE)
        response = self.post_move(asset, A.UNDER_MAINTENANCE, "screen cracked")
        self.assertRedirects(response, reverse("assets:detail", args=[asset.pk]))
        self.assertEqual(Asset.objects.get(pk=asset.pk).status, A.UNDER_MAINTENANCE)
        page = self.client.get(reverse("assets:history", args=[asset.pk]))
        self.assertContains(page, "screen cracked")
        self.assertContains(page, "Available → UnderMaintenance")
        self.assertContains(page, self.custodian.name)

    def test_typed_illegal_move_is_refused(self):
        asset = make_asset(owner_department=self.dept, status=A.AVAILABLE)
        response = self.post_move(asset, A.IN_USE)
        self.assertEqual(Asset.objects.get(pk=asset.pk).status, A.AVAILABLE)
        self.assertContains(self.client.get(response.url), "cannot be moved")

    def test_service_only_move_is_refused_on_the_page(self):
        # Available -> Reserved is a real arrow, but only the request service may make it.
        asset = make_asset(owner_department=self.dept, status=A.AVAILABLE)
        self.post_move(asset, A.RESERVED)
        self.assertEqual(Asset.objects.get(pk=asset.pk).status, A.AVAILABLE)

    def test_other_department_gets_403(self):
        theirs = make_asset(owner_department=self.other_dept, status=A.AVAILABLE)
        self.assertEqual(self.post_move(theirs, A.UNDER_MAINTENANCE).status_code, 403)
        self.assertEqual(self.client.get(reverse("assets:history", args=[theirs.pk])).status_code, 403)
        self.assertEqual(Asset.objects.get(pk=theirs.pk).status, A.AVAILABLE)

    def test_requester_gets_403(self):
        requester = with_role(make_user(department=self.dept), "Requester")
        asset = make_asset(owner_department=self.dept, status=A.AVAILABLE)
        self.client.login(email=requester.email, password=PASSWORD)
        self.assertEqual(self.post_move(asset, A.UNDER_MAINTENANCE).status_code, 403)

    def test_detail_page_shows_status_form_and_history(self):
        asset = make_asset(owner_department=self.dept, status=A.DRAFT)
        page = self.client.get(reverse("assets:detail", args=[asset.pk]))
        self.assertContains(page, 'value="Available"')
        self.assertContains(page, reverse("assets:history", args=[asset.pk]))
