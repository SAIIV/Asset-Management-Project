"""Reservations, Approvals & Transfers (store D4): Reservation, Approval, Transfer."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from circular_campus.choices import (
    ApprovalDecision,
    Condition,
    ReservationStatus,
    TransferStatus,
    TransferType,
    choices_check,
)


class Reservation(models.Model):
    """One unit held for one request. Only one Active reservation per asset."""

    id = models.BigAutoField(primary_key=True, db_column="reservationId")
    request = models.ForeignKey(
        "exchange.ResourceRequest", on_delete=models.CASCADE, related_name="reservations", db_column="requestId"
    )
    asset = models.ForeignKey("assets.Asset", on_delete=models.PROTECT, related_name="reservations", db_column="assetId")
    status = models.CharField(max_length=20, choices=ReservationStatus.choices, default=ReservationStatus.ACTIVE)
    reserved_at = models.DateTimeField(auto_now_add=True, db_column="reservedAt")
    released_at = models.DateTimeField(null=True, blank=True, db_column="releasedAt")

    class Meta:
        db_table = "Reservation"
        constraints = [
            choices_check("status", ReservationStatus, "reservation_status_valid"),
            # Partial unique index: the last unit can never be held for two requests.
            models.UniqueConstraint(
                fields=["asset"], condition=Q(status=ReservationStatus.ACTIVE), name="one_active_reservation_per_asset"
            ),
        ]


class Approval(models.Model):
    """A person's decision on a request or on a lifecycle proposal.

    Exactly one of requestId or lifecycleActionId is filled (CHECK constraint).
    The approver is never the requester (BR-02): checked in clean() and in the
    approval service, because it compares two different tables.
    """

    id = models.BigAutoField(primary_key=True, db_column="approvalId")
    request = models.ForeignKey(
        "exchange.ResourceRequest", on_delete=models.CASCADE, null=True, blank=True, related_name="approvals",
        db_column="requestId",
    )
    lifecycle_action = models.ForeignKey(
        "assets.LifecycleAction", on_delete=models.CASCADE, null=True, blank=True, related_name="approvals",
        db_column="lifecycleActionId",
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="approvals", db_column="approverId"
    )
    decision = models.CharField(max_length=30, choices=ApprovalDecision.choices, default=ApprovalDecision.PENDING)
    reason = models.TextField(blank=True)
    ai_score_seen = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, db_column="aiScoreSeen")
    decided_at = models.DateTimeField(null=True, blank=True, db_column="decidedAt")

    class Meta:
        db_table = "Approval"
        constraints = [
            models.CheckConstraint(
                condition=(Q(request__isnull=False, lifecycle_action__isnull=True)
                           | Q(request__isnull=True, lifecycle_action__isnull=False)),
                name="approval_exactly_one_target",
            ),
            choices_check("decision", ApprovalDecision, "approval_decision_valid"),
        ]

    def clean(self):
        if self.request_id and self.approver_id and self.request.requester_id == self.approver_id:
            raise ValidationError("An approver cannot approve their own request (BR-02).")


class Transfer(models.Model):
    """Movement of one tracked asset for one request.

    assetId, requestId and approverId are required; the receiving department is
    the request's department. Custody moves only when the receiver confirms.
    """

    id = models.BigAutoField(primary_key=True, db_column="transferId")
    asset = models.ForeignKey("assets.Asset", on_delete=models.PROTECT, related_name="transfers", db_column="assetId")
    request = models.ForeignKey(
        "exchange.ResourceRequest", on_delete=models.PROTECT, related_name="transfers", db_column="requestId"
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="approved_transfers", db_column="approverId"
    )
    type = models.CharField(max_length=20, choices=TransferType.choices, default=TransferType.PERMANENT)
    status = models.CharField(max_length=20, choices=TransferStatus.choices, default=TransferStatus.DRAFT)
    released_at = models.DateTimeField(null=True, blank=True, db_column="releasedAt")
    received_at = models.DateTimeField(null=True, blank=True, db_column="receivedAt")
    condition_on_receipt = models.CharField(
        max_length=20, choices=Condition.choices, null=True, blank=True, db_column="conditionOnReceipt"
    )

    class Meta:
        db_table = "Transfer"
        constraints = [
            choices_check("type", TransferType, "transfer_type_valid"),
            choices_check("status", TransferStatus, "transfer_status_valid"),
            choices_check("condition_on_receipt", Condition, "transfer_condition_valid", allow_null=True),
            # A transfer is only Received once the receipt time is recorded.
            models.CheckConstraint(
                condition=~Q(status=TransferStatus.RECEIVED) | Q(received_at__isnull=False),
                name="transfer_received_has_time",
            ),
        ]
        indexes = [models.Index(fields=["status"], name="transfer_status_idx")]
