"""C9 Basic report: requests and transfers of my own department, on screen and as CSV."""

import csv
import io
from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from accounts.models import AuditLog, Role, UserRole
from circular_campus.choices import ApprovalDecision as D, AssetStatus as A
from circular_campus.test_utils import make_asset, make_department, make_user
from exchange.requests import RequestService
from reports.operational import request_rows, transfer_rows, write_csv
from transfers.models import Transfer
from transfers.services import TransferService

PASSWORD = "Test-pass-123"


def with_role(user, name):
    UserRole.objects.create(user=user, role=Role.objects.get_or_create(name=name)[0])
    return user


class ReportTests(TestCase):
    def setUp(self):
        self.chem, self.it, self.lib = (make_department(name="Chemistry"), make_department(name="IT Services"),
                                        make_department(name="Library"))
        self.requester = with_role(make_user(department=self.chem, name="Rana Requester"), "Requester")
        self.custodian = with_role(make_user(department=self.it), "Custodian")
        self.approver = with_role(make_user(department=self.it, name="Amal Approver"), "Approver")
        self.monitor = make_asset(name="Dell monitor", owner_department=self.it, status=A.AVAILABLE, is_listed=True)
        self.req = RequestService.create(self.requester, {
            "purpose": "Lab screens", "quantity": 1, "required_by": date.today() + timedelta(days=7),
            "urgency": "Normal", "type": "Permanent", "mandatory_specs": [], "preferred_condition": "",
            "candidates": [self.monitor],
        })
        TransferService.reserve(self.custodian, self.req, [self.monitor])
        TransferService.decide(self.approver, self.req, D.APPROVED, "ok")
        self.transfer = Transfer.objects.get()
        TransferService.release(self.custodian, self.transfer)
        TransferService.receive(self.requester, self.transfer, "Good")

    def test_received_transfer_keeps_its_sender(self):
        # After receipt the monitor belongs to Chemistry, but the report still shows where it came from.
        row = transfer_rows(self.it.pk)[0]
        self.assertEqual((row["from_department"], row["to_department"]), ("IT Services", "Chemistry"))
        self.assertEqual((row["status"], row["approved_by"], row["condition"]), ("Received", "Amal Approver", "Good"))
        self.assertEqual(len(transfer_rows(self.chem.pk)), 1)  # the receiver sees it too
        self.assertEqual(transfer_rows(self.lib.pk), [])        # nobody else does

    def test_period_filter(self):
        self.assertEqual(len(transfer_rows(self.it.pk, start=date.today())), 1)
        self.assertEqual(transfer_rows(self.it.pk, end=date.today() - timedelta(days=1)), [])

    def test_request_rows_of_own_department(self):
        rows = request_rows(self.chem.pk)
        self.assertEqual([(r["request"], r["status"], r["reserved"]) for r in rows], [(f"#{self.req.pk}", "Fulfilled", 1)])
        self.assertEqual(request_rows(self.it.pk), [])

    def test_csv_blocks_formulas(self):
        out = io.StringIO()
        write_csv([{"a": "=HYPERLINK(1)", "b": "ok"}], [("a", "A"), ("b", "B")], out)
        self.assertEqual(list(csv.reader(io.StringIO(out.getvalue())))[1], ["'=HYPERLINK(1)", "ok"])

    def test_page_and_csv_export(self):
        self.client.login(email=self.custodian.email, password=PASSWORD)
        page = self.client.get(reverse("reports:operational"))
        self.assertContains(page, f"T-{self.transfer.pk:04d}")
        self.assertContains(page, "Dell monitor")
        response = self.client.get(reverse("reports:operational"), {"report": "transfers", "format": "csv"})
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        lines = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
        self.assertEqual(lines[0][0], "Transfer")
        self.assertEqual(lines[1][1], "Dell monitor")
        self.assertTrue(AuditLog.objects.filter(action="export_report").exists())

    def test_requests_report_page(self):
        approver_chem = with_role(make_user(department=self.chem), "Approver")
        self.client.login(email=approver_chem.email, password=PASSWORD)
        self.assertContains(self.client.get(reverse("reports:operational"), {"report": "requests"}), "Lab screens")

    def test_requester_cannot_run_reports(self):
        self.client.login(email=self.requester.email, password=PASSWORD)
        self.assertEqual(self.client.get(reverse("reports:operational")).status_code, 403)

    def test_bad_period_shows_error(self):
        self.client.login(email=self.custodian.email, password=PASSWORD)
        response = self.client.get(reverse("reports:operational"),
                                   {"start": "2026-12-01", "end": "2026-11-01"})
        self.assertContains(response, "start date is after the end date")
