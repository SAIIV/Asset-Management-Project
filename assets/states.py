"""C6 States and history: the state diagrams of Design Document Section 8.5.

Every status column is changed in one place only:

    StateService.move(user, record, new_status, reason="...", action="report_fault")

move() checks the move against the diagram of that record type, saves the new
status and writes one audit-log row (who, what, when, old and new status,
reason). A move that is not an arrow in the diagram raises IllegalMove, so it
cannot happen from a view, a form, the admin, or a typed URL.

Diagrams (state names are the Phase 3 status values):
  * Figure 56     Asset
  * Figure 57(a)  ResourceRequest      Figure 57(b)  Approval
  * Figure 58(a)  Transfer             Figure 58(b)  Reservation
"""

from django.db import transaction
from django.db.models import F

from accounts.services import AuditService
from circular_campus.choices import (
    ApprovalDecision as D,
    AssetStatus as A,
    RequestStatus as R,
    ReservationStatus as V,
    TransferStatus as T,
)

# (from, to) -> name of the event on the arrow. Only these moves exist.
ASSET_MOVES = {
    (A.DRAFT, A.AVAILABLE): "complete fields + serviceable (UC-06)",
    (A.AVAILABLE, A.RESERVED): "reserve full quantity (UC-13)",
    (A.RESERVED, A.AVAILABLE): "reject / cancel",
    (A.RESERVED, A.IN_TRANSIT): "approve + release (UC-14, UC-16)",
    (A.RESERVED, A.UNDER_MAINTENANCE): "fault while reserved",
    (A.IN_TRANSIT, A.IN_USE): "all units confirmed (UC-17)",
    (A.IN_TRANSIT, A.UNDER_MAINTENANCE): "damaged delivery accepted",
    (A.IN_TRANSIT, A.AVAILABLE): "loan return received",
    (A.IN_USE, A.IN_TRANSIT): "loan return released (UC-18)",
    (A.IN_USE, A.UNDER_MAINTENANCE): "fault / failed inspection",
    (A.AVAILABLE, A.UNDER_MAINTENANCE): "fault / failed inspection / planned repair (UC-19, UC-21)",
    (A.UNDER_MAINTENANCE, A.AVAILABLE): "passed inspection, held by owner (UC-22)",
    (A.UNDER_MAINTENANCE, A.IN_USE): "passed inspection, held by borrower",
    (A.AVAILABLE, A.RETIRED): "approved lifecycle action executed (UC-25)",
    (A.UNDER_MAINTENANCE, A.RETIRED): "approved lifecycle action executed (UC-25)",
    (A.IN_USE, A.RETIRED): "approved lifecycle action executed (UC-25)",
}

REQUEST_MOVES = {
    (R.DRAFT, R.SUBMITTED): "submit",
    (R.SUBMITTED, R.UNDER_REVIEW): "reserve all (UC-13)",
    (R.UNDER_REVIEW, R.SUBMITTED): "returned for correction / allocation released",
    (R.UNDER_REVIEW, R.APPROVED): "approve (approver is not the requester)",
    (R.UNDER_REVIEW, R.REJECTED): "reject with reason",
    (R.APPROVED, R.SUBMITTED): "material change: new version and approval (BR-06)",
    (R.APPROVED, R.FULFILLED): "receiver confirms all units (UC-17)",
    (R.DRAFT, R.CANCELLED): "cancel",
    (R.SUBMITTED, R.CANCELLED): "cancel",
    (R.UNDER_REVIEW, R.CANCELLED): "cancel before dispatch (releases allocation)",
    (R.APPROVED, R.CANCELLED): "cancel before dispatch (releases allocation)",
}

APPROVAL_MOVES = {
    (D.PENDING, D.APPROVED): "approve(reason)",
    (D.PENDING, D.REJECTED): "reject(reason)",
    (D.PENDING, D.RETURNED_FOR_CORRECTION): "return(reason)",
    (D.APPROVED, D.INVALIDATED): "material change before dispatch (BR-06)",
}

TRANSFER_MOVES = {
    (T.DRAFT, T.SCHEDULED): "schedule (UC-15)",
    (T.DRAFT, T.CANCELLED): "cancel",
    (T.SCHEDULED, T.DISPATCHED): "release (UC-16)",
    (T.SCHEDULED, T.CANCELLED): "cancel before dispatch",
    (T.DISPATCHED, T.RECEIVED): "all units confirmed (UC-17)",
    (T.DISPATCHED, T.DISPUTED): "mismatch / damage",
    (T.DISPUTED, T.RECEIVED): "documented resolution",
}

RESERVATION_MOVES = {
    (V.ACTIVE, V.CONSUMED): "release",
    (V.ACTIVE, V.RELEASED): "reject / cancel / reassign",
}

#: model name -> (name of its status field, its diagram)
DIAGRAMS = {
    "Asset": ("status", ASSET_MOVES),
    "ResourceRequest": ("status", REQUEST_MOVES),
    "Approval": ("decision", APPROVAL_MOVES),
    "Transfer": ("status", TRANSFER_MOVES),
    "Reservation": ("status", RESERVATION_MOVES),
}

#: Asset moves a custodian makes by hand on the asset page. All other asset
#: moves (reserve, release, receive, retire) are made by the request, transfer
#: and lifecycle services, never typed in directly.
CUSTODIAN_ASSET_MOVES = {
    (A.DRAFT, A.AVAILABLE),
    (A.AVAILABLE, A.UNDER_MAINTENANCE),
    (A.IN_USE, A.UNDER_MAINTENANCE),
    (A.UNDER_MAINTENANCE, A.AVAILABLE),
    (A.UNDER_MAINTENANCE, A.IN_USE),
}

#: Leaving the catalogue: an asset in these states is never listed (Figure 56 notes).
UNLISTED_STATES = {A.DRAFT, A.IN_USE, A.UNDER_MAINTENANCE, A.RETIRED}


class IllegalMove(Exception):
    """The move is not an arrow of the state diagram; the message is shown to the user."""


def _diagram(record):
    # Asset subclasses (ITAsset, LabEquipment, FurnitureAsset) use the Asset diagram.
    for cls in type(record).__mro__:
        if cls.__name__ in DIAGRAMS:
            return cls, DIAGRAMS[cls.__name__]
    raise IllegalMove(f"{type(record).__name__} has no state diagram.")


def allowed_moves(record):
    """The states this record may move to next, with the event name of each arrow."""
    _, (field, moves) = _diagram(record)
    current = getattr(record, field)
    return {to: event for (frm, to), event in moves.items() if frm == current}


def custodian_moves(asset):
    """The next states a custodian may choose by hand on the asset page."""
    return {to: event for to, event in allowed_moves(asset).items() if (asset.status, to) in CUSTODIAN_ASSET_MOVES}


def is_allowed(record_type, frm, to):
    """True if (frm -> to) is an arrow in the diagram of record_type, e.g. is_allowed("Asset", "Draft", "InUse")."""
    return (frm, to) in DIAGRAMS[record_type][1]


class StateService:
    @staticmethod
    @transaction.atomic
    def move(user, record, new_status, *, reason="", action=None):
        """Move the record to new_status if the diagram allows it, and write the audit row.

        The row is locked while it changes (SELECT ... FOR UPDATE), so two
        people pressing a button at the same moment cannot both move it.
        Returns the record, reloaded with its new status.
        """
        base, (field, moves) = _diagram(record)
        locked = base.objects.select_for_update().get(pk=record.pk)
        current = getattr(locked, field)
        if (current, new_status) not in moves:
            raise IllegalMove(
                f"{base.__name__} #{record.pk} cannot move from {current} to {new_status}: "
                f"that move is not in the state diagram."
            )
        changes = {field: new_status}
        if base.__name__ == "Asset":
            changes["version"] = F("version") + 1  # an open edit form of the old state is refused (C2)
            if new_status in UNLISTED_STATES:
                changes["is_listed"] = False
        base.objects.filter(pk=record.pk).update(**changes)
        AuditService.log(
            user, action or f"{base.__name__.lower()}_{field}_change", record_type=base.__name__,
            record_id=record.pk, before={field: current}, after={field: new_status},
            reason=reason or moves[(current, new_status)],
        )
        record.refresh_from_db()
        return record


def history_of(record_type, record_id):
    """Every audit event about one record, newest first: who did what, when and why (C6)."""
    from accounts.models import AuditLog
    return (AuditLog.objects.filter(record_type=record_type, record_id=record_id)
            .select_related("user").order_by("-created_at", "-id"))
