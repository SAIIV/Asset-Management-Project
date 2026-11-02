"""All enumerations of the data model, in one place.

The values are the exact state and enum names of the Design Document
(Section 8.2 class diagram enumerations and Section 8.5 state diagrams), so the
code, the database and the requirements use the same words. Every status
column stores one of these values, and the database rejects any other value
(see the CHECK constraints in each model's Meta).
"""

from django.db import models


class Condition(models.TextChoices):
    """Physical condition of an asset (class diagram enumeration Condition)."""
    NEW = "New", "New"
    GOOD = "Good", "Good"
    FAIR = "Fair", "Fair"
    NEEDS_REPAIR = "NeedsRepair", "Needs repair"


class AssetStatus(models.TextChoices):
    """Asset life-cycle states (Figure 56)."""
    DRAFT = "Draft", "Draft"
    AVAILABLE = "Available", "Available"
    RESERVED = "Reserved", "Reserved"
    IN_TRANSIT = "InTransit", "In transit"
    IN_USE = "InUse", "In use"
    UNDER_MAINTENANCE = "UnderMaintenance", "Under maintenance"
    RETIRED = "Retired", "Retired"


class RequestStatus(models.TextChoices):
    """Resource request states (Figure 57a)."""
    DRAFT = "Draft", "Draft"
    SUBMITTED = "Submitted", "Submitted"
    UNDER_REVIEW = "UnderReview", "Under review"
    APPROVED = "Approved", "Approved"
    REJECTED = "Rejected", "Rejected"
    CANCELLED = "Cancelled", "Cancelled"
    FULFILLED = "Fulfilled", "Fulfilled"


class Urgency(models.TextChoices):
    """Request urgency; sets the ready-by slack of the score (Section 11.1)."""
    HIGH = "High", "High"
    NORMAL = "Normal", "Normal"
    LOW = "Low", "Low"


class TransferType(models.TextChoices):
    """Kind of request / transfer (class diagram type: TransferType; UC-18 loans)."""
    PERMANENT = "Permanent", "Permanent transfer"
    LOAN = "Loan", "Loan"
    RETURN = "Return", "Loan return"


class ApprovalDecision(models.TextChoices):
    """Approval states (Figure 57b). The AI has no transition here."""
    PENDING = "Pending", "Pending"
    APPROVED = "Approved", "Approved"
    REJECTED = "Rejected", "Rejected"
    RETURNED_FOR_CORRECTION = "ReturnedForCorrection", "Returned for correction"
    INVALIDATED = "Invalidated", "Invalidated"


class TransferStatus(models.TextChoices):
    """Transfer states (Figure 58a)."""
    DRAFT = "Draft", "Draft"
    SCHEDULED = "Scheduled", "Scheduled"
    DISPATCHED = "Dispatched", "Dispatched"
    RECEIVED = "Received", "Received"
    DISPUTED = "Disputed", "Disputed"
    CANCELLED = "Cancelled", "Cancelled"


class ReservationStatus(models.TextChoices):
    """Reservation states (Figure 58b)."""
    ACTIVE = "Active", "Active"
    CONSUMED = "Consumed", "Consumed"
    RELEASED = "Released", "Released"


class LifecycleActionType(models.TextChoices):
    """What a lifecycle proposal does (data dictionary: donation, recycling or disposal)."""
    DONATION = "Donation", "Donation"
    RECYCLING = "Recycling", "Recycling"
    DISPOSAL = "Disposal", "Disposal"


class LifecycleStatus(models.TextChoices):
    """Lifecycle proposal states (Figure 58c)."""
    PROPOSED = "Proposed", "Proposed"
    APPROVED = "Approved", "Approved"
    REJECTED = "Rejected", "Rejected"
    EXECUTED = "Executed", "Executed"
    CANCELLED = "Cancelled", "Cancelled"


class MaintenanceStatus(models.TextChoices):
    """Maintenance job states (UC-19 to UC-22 sequences)."""
    REPORTED = "Reported", "Reported"
    SCHEDULED = "Scheduled", "Scheduled"
    IN_PROGRESS = "InProgress", "In progress"
    COMPLETED = "Completed", "Completed"
    CANCELLED = "Cancelled", "Cancelled"


class FileKind(models.TextChoices):
    """Attachment kind (class diagram FileKind: photo | pdf)."""
    PHOTO = "photo", "Photo"
    PDF = "pdf", "Specification PDF"


class RoleName(models.TextChoices):
    """The eight Phase 3 actors (Section 6.1). Prototype 1 uses the first four."""
    REQUESTER = "Requester", "Requester"
    CUSTODIAN = "Custodian", "Custodian"
    APPROVER = "Approver", "Approver"
    ADMINISTRATOR = "Administrator", "Administrator"
    FINANCE_OFFICER = "FinanceOfficer", "Finance Officer"
    MAINTENANCE_OFFICER = "MaintenanceOfficer", "Maintenance Officer"
    SUSTAINABILITY_OFFICER = "SustainabilityOfficer", "Sustainability Officer"
    AUDITOR = "Auditor", "Auditor"


class MatchDecision(models.TextChoices):
    """The requester's answer to one ranked candidate (gate 2)."""
    ACCEPTED = "Accepted", "Accepted"
    REJECTED = "Rejected", "Rejected"


class AITask(models.TextChoices):
    """AI tasks of the gateway (Section 10.1)."""
    CLASSIFY_ASSET = "classify_asset", "Classify asset"
    RANK_MATCHES = "rank_matches", "Rank matches"
    RECOMMEND_ACTION = "recommend_action", "Recommend action"
    ANSWER_QUESTION = "answer_question", "Answer question"
    DRAFT_SUMMARY = "draft_summary", "Draft summary"


class AIDecision(models.TextChoices):
    """A person's answer to an AI suggestion (Section 13: accepted, corrected or rejected)."""
    ACCEPTED = "Accepted", "Accepted"
    CORRECTED = "Corrected", "Corrected"
    REJECTED = "Rejected", "Rejected"


class ModelKind(models.TextChoices):
    """What a ModelVersion row describes (model, prompt, ranking weights)."""
    EMBEDDING = "Embedding", "Embedding model"
    TEXT_GENERATION = "TextGeneration", "Text generation model and prompt"
    RANKING = "Ranking", "Ranking weights and thresholds"


def choices_check(field, choices_class, name, allow_null=False):
    """Build a CHECK constraint so the database itself only accepts enum values."""
    q = models.Q(**{f"{field}__in": choices_class.values})
    if allow_null:
        q |= models.Q(**{f"{field}__isnull": True})
    return models.CheckConstraint(condition=q, name=name)
