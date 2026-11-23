"""seed_data --history: demo requests go through the real workflow, so the dashboard has figures."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from circular_campus.choices import RequestStatus, TransferStatus, TransferType
from exchange.models import RequestSpecification, ResourceRequest
from reports.sustainability import dashboard, sync_impacts
from transfers.models import Transfer


class SeedHistoryTests(TestCase):
    def test_history_fills_the_dashboard_and_runs_only_once(self):
        call_command("seed_data", "--history", stdout=StringIO())
        received = Transfer.objects.filter(status=TransferStatus.RECEIVED, type=TransferType.PERMANENT)
        self.assertGreaterEqual(received.count(), 3)
        self.assertTrue(ResourceRequest.objects.filter(status=RequestStatus.UNDER_REVIEW).exists())
        self.assertTrue(ResourceRequest.objects.filter(status=RequestStatus.SUBMITTED).exists())

        sync_impacts()
        figures = dashboard()
        self.assertEqual(figures["reuse_count"], received.count())
        self.assertIsNotNone(figures["co2e_kg"])  # EPA WARM factors are filled in
        self.assertGreater(figures["published_assets"], figures["reuse_count"])

        requests = RequestSpecification.objects.filter(purpose__startswith="SYNTHETIC demo history").count()
        out = StringIO()
        call_command("seed_data", "--history", stdout=out)
        self.assertIn("already exists", out.getvalue())
        self.assertEqual(RequestSpecification.objects.filter(purpose__startswith="SYNTHETIC demo history").count(),
                         requests)

    def test_plain_seed_adds_no_history(self):
        call_command("seed_data", stdout=StringIO())
        self.assertFalse(Transfer.objects.exists())
