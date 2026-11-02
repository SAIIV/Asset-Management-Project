"""Tests for ModelVersion and AIRecord (insert-only records, Section 13)."""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from ai.models import AIRecord, ModelVersion
from circular_campus.test_utils import now


class AIRecordTests(TestCase):
    def setUp(self):
        self.version = ModelVersion.objects.create(kind="Embedding", name="all-MiniLM-L6-v2", active_from=now())

    def test_model_version_rows_are_never_edited(self):
        self.version.name = "changed"
        with self.assertRaises(ValidationError):
            self.version.save()

    def test_task_must_be_a_gateway_task(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            AIRecord.objects.create(model_version=self.version, task="tell_a_joke")

    def test_decision_filled_once_other_fields_never(self):
        record = AIRecord.objects.create(model_version=self.version, task="classify_asset", score=0.72)
        record.output = {"changed": True}
        with self.assertRaises(ValidationError):
            record.save()
        record.decision = "Accepted"
        record.save(update_fields=["decision"])  # allowed once
        record.decision = "Rejected"
        with self.assertRaises(ValidationError):
            record.save(update_fields=["decision"])
