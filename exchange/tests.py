"""Tests for ResourceRequest, RequestSpecification and MatchRecommendation."""

from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from circular_campus.test_utils import make_asset, make_request
from exchange.models import MatchRecommendation, RequestSpecification, ResourceRequest


class ResourceRequestTests(TestCase):
    def test_quantity_at_least_one(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_request(quantity=0)
        self.assertEqual(make_request(quantity=1).quantity, 1)

    def test_new_request_starts_as_draft_version_1(self):
        request = make_request()
        self.assertEqual((request.status, request.version), ("Draft", 1))

    def test_status_only_accepts_enum_values(self):
        request = make_request()
        with self.assertRaises(IntegrityError), transaction.atomic():
            ResourceRequest.objects.filter(pk=request.pk).update(status="Lost")

    def test_required_by_not_in_past_at_submission(self):
        request = make_request(status="Submitted", required_by=date.today() - timedelta(days=1))
        with self.assertRaises(ValidationError):
            request.clean()


class RequestSpecificationTests(TestCase):
    def test_one_specification_per_request_deleted_with_request(self):
        request = make_request()
        RequestSpecification.objects.create(request=request, purpose="Teaching lab", mandatory_specs=["24 inch"])
        with self.assertRaises(IntegrityError), transaction.atomic():
            RequestSpecification.objects.create(request=request, purpose="Again")
        request.delete()
        self.assertFalse(RequestSpecification.objects.exists())

    def test_preferred_condition_must_be_a_condition(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            RequestSpecification.objects.create(request=make_request(), purpose="x", preferred_condition="Shiny")


class MatchRecommendationTests(TestCase):
    def test_score_between_0_and_100(self):
        request, asset = make_request(), make_asset()
        for bad in (-1, 101):
            with self.assertRaises(IntegrityError), transaction.atomic():
                MatchRecommendation.objects.create(request=request, asset=asset, score=bad, rank_position=1)
        match = MatchRecommendation.objects.create(request=request, asset=asset, score=84, rank_position=1)
        self.assertIsNone(match.decision)  # empty until the requester acts
