"""Search & Requests (store D3): ResourceRequest, RequestSpecification, MatchRecommendation."""

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from circular_campus.choices import Condition, MatchDecision, RequestStatus, TransferType, Urgency, choices_check


class ResourceRequest(models.Model):
    """What a department needs (data dictionary: ResourceRequest).

    quantity >= 1; requiredBy not in the past at submission; a material change
    creates a new version (BR-06).
    """

    id = models.BigAutoField(primary_key=True, db_column="requestId")
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="requests", db_column="requesterId"
    )
    quantity = models.PositiveIntegerField(default=1)
    urgency = models.CharField(max_length=10, choices=Urgency.choices, default=Urgency.NORMAL)
    required_by = models.DateField(db_column="requiredBy")
    type = models.CharField(max_length=20, choices=TransferType.choices, default=TransferType.PERMANENT)
    status = models.CharField(max_length=20, choices=RequestStatus.choices, default=RequestStatus.DRAFT)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "ResourceRequest"
        ordering = ["-id"]
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gte=1), name="request_quantity_at_least_one"),
            choices_check("urgency", Urgency, "request_urgency_valid"),
            choices_check("type", TransferType, "request_type_valid"),
            choices_check("status", RequestStatus, "request_status_valid"),
            models.CheckConstraint(condition=Q(version__gte=1), name="request_version_positive"),
        ]
        indexes = [models.Index(fields=["status"], name="request_status_idx")]

    def __str__(self):
        return f"Request #{self.pk} ({self.status})"

    @property
    def department(self):
        """The receiving department is the requester's department."""
        return self.requester.department

    def clean(self):
        # "requiredBy not in the past at submission": the date can only be
        # compared with today in code, not in a CHECK constraint.
        if self.status == RequestStatus.SUBMITTED and self.required_by and self.required_by < timezone.localdate():
            raise ValidationError({"required_by": "The required-by date cannot be in the past."})


class RequestSpecification(models.Model):
    """Purpose, mandatory specifications and preferred condition of one request.

    One per request (requestId unique); deleted with its request.
    """

    id = models.BigAutoField(primary_key=True, db_column="specId")
    request = models.OneToOneField(
        ResourceRequest, on_delete=models.CASCADE, related_name="specification", db_column="requestId"
    )
    purpose = models.TextField()
    mandatory_specs = ArrayField(models.TextField(), default=list, blank=True, db_column="mandatorySpecs")
    preferred_condition = models.CharField(
        max_length=20, choices=Condition.choices, null=True, blank=True, db_column="preferredCondition"
    )

    class Meta:
        db_table = "RequestSpecification"
        constraints = [
            choices_check("preferred_condition", Condition, "spec_preferred_condition_valid", allow_null=True),
        ]


class MatchRecommendation(models.Model):
    """One ranked candidate asset for one request (AI #2).

    score 0 to 100; factorScores holds the five factors S, T, R, C, E;
    decision stays empty until the requester acts.
    """

    id = models.BigAutoField(primary_key=True, db_column="matchId")
    request = models.ForeignKey(
        ResourceRequest, on_delete=models.CASCADE, related_name="matches", db_column="requestId"
    )
    asset = models.ForeignKey("assets.Asset", on_delete=models.CASCADE, related_name="matches", db_column="assetId")
    ai_record = models.ForeignKey(
        "ai.AIRecord", on_delete=models.PROTECT, null=True, blank=True, related_name="matches", db_column="aiRecordId"
    )
    score = models.DecimalField(max_digits=5, decimal_places=2)
    explanation = models.TextField(blank=True)
    model_version = models.CharField(max_length=60, blank=True, db_column="modelVersion")
    factor_scores = models.JSONField(default=dict, blank=True, db_column="factorScores")
    rank_position = models.PositiveSmallIntegerField(db_column="rankPosition")
    decision = models.CharField(max_length=10, choices=MatchDecision.choices, null=True, blank=True)

    class Meta:
        db_table = "MatchRecommendation"
        ordering = ["request", "rank_position"]
        constraints = [
            models.CheckConstraint(condition=Q(score__gte=0) & Q(score__lte=100), name="match_score_0_to_100"),
            models.CheckConstraint(condition=Q(rank_position__gte=1), name="match_rank_positive"),
            choices_check("decision", MatchDecision, "match_decision_valid", allow_null=True),
        ]
