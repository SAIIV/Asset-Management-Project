"""Maintenance and lifecycle (UC-19 to UC-25): faults, repairs, and donation / recycling / disposal.

    MaintenanceService.report_fault(user, asset, description)      UC-19 anyone with "report a fault"
    MaintenanceService.start_repair(custodian, record)             UC-21 asset -> Under maintenance
    MaintenanceService.finish_repair(custodian, record, cost, note)  UC-22 asset back to where it was
    MaintenanceService.cancel(custodian, record, reason)           fault closed without repair

    LifecycleService.propose(custodian, asset, kind, reason)       UC-23 custodian of the owner department
    LifecycleService.decide(approver, proposal, approve, reason)   UC-24 an approver who did not propose it
    LifecycleService.execute(custodian, proposal, evidence)        UC-25 asset -> Retired, evidence required
    LifecycleService.cancel(custodian, proposal, reason)

Rules kept here:
  * Asset status changes go through StateService (C6), so only Figure 56 arrows happen and each is audited.
  * Reporting a fault takes the item off the catalogue, so nobody requests a broken item; closing the
    fault as "no fault found" puts it back. While a fault or a retirement proposal is open, the item
    cannot be published or reserved (hold_reason).
  * Starting the repair of a Reserved unit follows the Figure 56 arrow "fault while reserved": the
    request's reservations are released, its scheduled transfers cancelled, an approval invalidated,
    and the request goes back to Submitted so another unit can be reserved. Everyone involved is told.
    This is refused once any unit of that request has been dispatched, and an In-transit unit is
    repaired by the receiving department after it confirms receipt.
  * Executing a retirement closes any open fault of the item.
  * The person who proposed a lifecycle action cannot authorize it (BR-02, separation of duties).
  * Executed needs evidence (data dictionary: LifecycleAction.executionEvidence).
  * Only one open proposal per asset; while it is open the asset is taken off the catalogue.
"""

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from accounts.models import AuditLog
from accounts.services import AuditService
from circular_campus.choices import (
    AssetStatus as A,
    LifecycleActionType,
    LifecycleStatus as L,
    MaintenanceStatus as M,
    RoleName,
)
from notifications.services import notify, notify_many

from .models import Asset, LifecycleAction, MaintenanceRecord
from .states import StateService

OPEN_FAULTS = [M.REPORTED, M.SCHEDULED, M.IN_PROGRESS]
OPEN_PROPOSALS = [L.PROPOSED, L.APPROVED]
#: Asset states with an arrow to UnderMaintenance that a custodian may start a repair from.
REPAIRABLE = [A.AVAILABLE, A.IN_USE]
#: Asset states with an arrow to Retired (Figure 56).
RETIRABLE = [A.AVAILABLE, A.UNDER_MAINTENANCE, A.IN_USE]


class MaintenanceError(Exception):
    """The step was refused; the message is shown to the user."""


def hold_reason(asset):
    """Why this unit may not be published or reserved right now, or None if it may."""
    if MaintenanceRecord.objects.filter(asset_id=asset.pk, status__in=OPEN_FAULTS).exists():
        return "it has an open fault report (repair or close it on the Maintenance page)"
    if LifecycleAction.objects.filter(asset_id=asset.pk, status__in=OPEN_PROPOSALS).exists():
        return "it is proposed for donation, recycling or disposal"
    return None


def without_held(assets):
    """The queryset without units that have an open fault or an open retirement proposal."""
    return (assets.exclude(pk__in=MaintenanceRecord.objects.filter(status__in=OPEN_FAULTS).values("asset_id"))
            .exclude(pk__in=LifecycleAction.objects.filter(status__in=OPEN_PROPOSALS).values("asset_id")))


def _withdraw_from_request(custodian, asset, record):
    """Fault while reserved (Figure 56): free the request this unit is reserved for. Returns the request or None."""
    from exchange.models import ResourceRequest
    from transfers.models import Approval, Reservation
    from circular_campus.choices import (ApprovalDecision as D, RequestStatus as R, ReservationStatus as V,
                                         TransferStatus as T)

    reservation = Reservation.objects.filter(asset_id=asset.pk, status=V.ACTIVE).first()
    if reservation is None:
        return None
    request = ResourceRequest.objects.select_for_update().get(pk=reservation.request_id)
    if request.transfers.filter(status__in=[T.DISPATCHED, T.DISPUTED, T.RECEIVED]).exists():
        raise MaintenanceError(f"Part of request #{request.pk} is already on its way, so this unit cannot be "
                               f"taken back now. Start the repair once the request is finished.")
    why = f"“{asset.name}” went for repair (fault #{record.pk})"
    departments = set()
    for held in Reservation.objects.filter(request=request, status=V.ACTIVE).select_related("asset"):
        StateService.move(custodian, held, V.RELEASED, action="release_reservation", reason=why)
        Reservation.objects.filter(pk=held.pk).update(released_at=timezone.now())
        if held.asset_id != asset.pk and held.asset.status == A.RESERVED:
            StateService.move(custodian, held.asset, A.AVAILABLE, action="release_asset",
                              reason=f"Request #{request.pk}: {why}")
            departments.add(held.asset.owner_department_id)
    for transfer in request.transfers.filter(status__in=[T.DRAFT, T.SCHEDULED]):
        StateService.move(custodian, transfer, T.CANCELLED, reason=why)
    approvers = []
    if request.status == R.APPROVED:
        for approval in Approval.objects.filter(request=request, decision=D.APPROVED):
            StateService.move(custodian, approval, D.INVALIDATED, action="invalidate_approval", reason=why)
            approvers.append(approval.approver)
    if request.status in (R.UNDER_REVIEW, R.APPROVED):
        StateService.move(custodian, request, R.SUBMITTED, action="return_request", reason=why)
    notify(request.requester, f"{why}, so it is no longer reserved for your request #{request.pk}. "
                              f"The request is back to Submitted so another unit can be reserved.", request)
    notify_many(approvers, f"Your approval of request #{request.pk} no longer applies: {why}.", request)
    for department in departments:
        notify_many(_users(RoleName.CUSTODIAN, department),
                    f"Request #{request.pk} was put back to Submitted ({why}); your reserved units are Available "
                    f"again.", request)
    return request


def _users(role, department_id=None):
    from accounts.models import User
    users = User.objects.filter(roles__name=role, is_active=True)
    if department_id is not None:
        users = users.filter(department_id=department_id)
    return users.distinct()


def reported_by(record):
    row = AuditLog.objects.filter(action="report_fault", record_type="MaintenanceRecord",
                                  record_id=record.pk).select_related("user").first()
    return row.user if row else None


def proposer_of(proposal):
    row = AuditLog.objects.filter(action="propose_lifecycle", record_type="LifecycleAction",
                                  record_id=proposal.pk).first()
    return row.user_id if row else None


def with_proposer(proposal):
    """Sets proposal.proposer_id, which the access matrix uses for "not your own" (permissions.py)."""
    proposal.proposer_id = proposer_of(proposal)
    return proposal


class MaintenanceService:
    @staticmethod
    @transaction.atomic
    def report_fault(user, asset, description):
        description = (description or "").strip()
        if not description:
            raise MaintenanceError("Describe the fault, for example \"screen flickers\" or \"wheel broken\".")
        if asset.status in (A.RETIRED, A.DRAFT):
            raise MaintenanceError(f"This item is {asset.get_status_display()}, so a fault cannot be reported.")
        if MaintenanceRecord.objects.filter(asset=asset, status__in=OPEN_FAULTS).exists():
            raise MaintenanceError("A fault is already open for this item. The custodian has been told.")
        record = MaintenanceRecord.objects.create(asset=asset, reported_at=timezone.now(), action=description)
        unlisted = asset.is_listed
        AuditService.log(user, "report_fault", record,
                         after={"asset": asset.pk, "fault": description, "unlisted": unlisted})
        if unlisted:  # nobody should request an item that may be broken
            Asset.objects.filter(pk=asset.pk).update(is_listed=False)
            AuditService.log(user, "unpublish_asset", asset, before={"is_listed": True},
                             after={"is_listed": False}, reason=f"fault #{record.pk} reported")
        notify_many([u for u in _users(RoleName.CUSTODIAN, asset.owner_department_id) if u.pk != user.pk],
                    f"Fault reported on “{asset.name}” by {user.name}: {description}", asset)
        notify(user, f"Your fault report for “{asset.name}” was sent to its custodian.")
        return record

    @staticmethod
    @transaction.atomic
    def start_repair(custodian, record):
        record = MaintenanceRecord.objects.select_for_update().select_related("asset").get(pk=record.pk)
        if record.status != M.REPORTED:
            raise MaintenanceError(f"This repair is already {record.get_status_display()}.")
        asset = Asset.objects.select_for_update().get(pk=record.asset_id)
        if asset.status == A.IN_TRANSIT:
            raise MaintenanceError(f"“{asset.name}” is on its way to another department. The receiving "
                                   f"department starts the repair after it confirms receipt.")
        if asset.status not in REPAIRABLE + [A.RESERVED, A.UNDER_MAINTENANCE]:
            raise MaintenanceError(f"“{asset.name}” is {asset.get_status_display()}, so it cannot be repaired.")
        before = asset.status
        if asset.status == A.RESERVED:
            _withdraw_from_request(custodian, asset, record)
            before = A.AVAILABLE  # after the repair it is back with its owner, not reserved
        if asset.status == A.UNDER_MAINTENANCE:
            before = A.AVAILABLE  # already moved by hand on the asset page
        else:
            StateService.move(custodian, asset, A.UNDER_MAINTENANCE, action="start_repair",
                              reason=f"repair of fault #{record.pk}: {record.action}")
        MaintenanceRecord.objects.filter(pk=record.pk).update(status=M.IN_PROGRESS)
        AuditService.log(custodian, "start_repair", record, before={"status": M.REPORTED},
                         after={"status": M.IN_PROGRESS, "asset_was": before})
        record.refresh_from_db()
        return record

    @staticmethod
    @transaction.atomic
    def finish_repair(custodian, record, cost="", note=""):
        record = MaintenanceRecord.objects.select_for_update().select_related("asset").get(pk=record.pk)
        if record.status != M.IN_PROGRESS:
            raise MaintenanceError("Only a repair in progress can be finished.")
        try:
            cost = Decimal(str(cost).strip()) if str(cost or "").strip() else None
        except InvalidOperation:
            raise MaintenanceError("The cost must be a number in AED, for example 120.50.") from None
        if cost is not None and cost < 0:
            raise MaintenanceError("The cost cannot be negative.")
        started = AuditLog.objects.filter(action="start_repair", record_type="MaintenanceRecord",
                                          record_id=record.pk).first()
        back_to = (started.after_value or {}).get("asset_was", A.AVAILABLE) if started else A.AVAILABLE
        if back_to not in REPAIRABLE:
            back_to = A.AVAILABLE
        if Asset.objects.get(pk=record.asset_id).status == A.UNDER_MAINTENANCE:  # not if it was retired meanwhile
            StateService.move(custodian, record.asset, back_to, action="finish_repair",
                              reason=f"repair of fault #{record.pk} done" + (f": {note}" if note else ""))
        MaintenanceRecord.objects.filter(pk=record.pk).update(status=M.COMPLETED, completed_at=timezone.now(),
                                                              cost=cost)
        AuditService.log(custodian, "finish_repair", record, before={"status": M.IN_PROGRESS},
                         after={"status": M.COMPLETED, "cost": str(cost) if cost is not None else None},
                         reason=note)
        reporter = reported_by(record)
        if reporter and reporter.pk != custodian.pk:
            notify(reporter, f"The fault you reported on “{record.asset.name}” was repaired.")
        record.refresh_from_db()
        return record

    @staticmethod
    @transaction.atomic
    def cancel(custodian, record, reason):
        reason = (reason or "").strip()
        if not reason:
            raise MaintenanceError("Give a reason, for example \"no fault found\".")
        record = MaintenanceRecord.objects.select_for_update().get(pk=record.pk)
        if record.status != M.REPORTED:
            raise MaintenanceError("Only a fault that is not being repaired yet can be closed.")
        MaintenanceRecord.objects.filter(pk=record.pk).update(status=M.CANCELLED)
        AuditService.log(custodian, "close_fault", record, before={"status": M.REPORTED},
                         after={"status": M.CANCELLED}, reason=reason)
        _relist_if_report_unlisted(custodian, record)
        reporter = reported_by(record)
        if reporter and reporter.pk != custodian.pk:
            notify(reporter, f"Your fault report #{record.pk} was closed: {reason}")
        record.refresh_from_db()
        return record


def _relist_if_report_unlisted(user, record):
    """A fault closed without repair puts the item back in the catalogue if the report took it out."""
    from exchange.catalogue import publish_problems

    row = AuditLog.objects.filter(action="report_fault", record_type="MaintenanceRecord", record_id=record.pk).first()
    asset = Asset.objects.get(pk=record.asset_id)
    if (row and (row.after_value or {}).get("unlisted") and asset.status == A.AVAILABLE and not asset.is_listed
            and not publish_problems(asset)):
        Asset.objects.filter(pk=asset.pk).update(is_listed=True)
        AuditService.log(user, "publish_asset", asset, before={"is_listed": False}, after={"is_listed": True},
                         reason=f"fault #{record.pk} closed without repair")


class LifecycleService:
    @staticmethod
    @transaction.atomic
    def propose(custodian, asset, kind, reason):
        reason = (reason or "").strip()
        if kind not in LifecycleActionType.values:
            raise MaintenanceError("Choose donation, recycling or disposal.")
        if not reason:
            raise MaintenanceError("Give a reason, for example \"beyond economic repair\".")
        asset = Asset.objects.select_for_update().get(pk=asset.pk)
        if asset.status not in RETIRABLE:
            raise MaintenanceError(f"“{asset.name}” is {asset.get_status_display()}; it can only be retired "
                                   f"when Available, In use or Under maintenance.")
        if LifecycleAction.objects.filter(asset=asset, status__in=OPEN_PROPOSALS).exists():
            raise MaintenanceError("This item already has an open proposal.")
        proposal = LifecycleAction.objects.create(asset=asset, action=kind, reason=reason)
        AuditService.log(custodian, "propose_lifecycle", proposal, after={"asset": asset.pk, "action": kind},
                         reason=reason)
        if asset.is_listed:  # an item about to leave the university is not offered to others
            Asset.objects.filter(pk=asset.pk).update(is_listed=False)
            AuditService.log(custodian, "unpublish_asset", asset, before={"is_listed": True},
                             after={"is_listed": False}, reason=f"{kind} proposed")
        notify_many([u for u in _users(RoleName.APPROVER) if u.pk != custodian.pk],
                    f"{custodian.department}: {kind.lower()} of “{asset.name}” proposed ({reason}). "
                    f"Please approve or reject it.")
        return with_proposer(proposal)

    @staticmethod
    @transaction.atomic
    def decide(approver, proposal, approve, reason=""):
        reason = (reason or "").strip()
        proposal = LifecycleAction.objects.select_for_update().select_related("asset").get(pk=proposal.pk)
        if proposal.status != L.PROPOSED:
            raise MaintenanceError(f"This proposal is already {proposal.get_status_display()}.")
        if proposer_of(proposal) == approver.pk:
            raise MaintenanceError("You proposed this yourself, so another approver must decide (BR-02).")
        if not approve and not reason:
            raise MaintenanceError("Give a reason when you reject a proposal.")
        new = L.APPROVED if approve else L.REJECTED
        LifecycleAction.objects.filter(pk=proposal.pk).update(status=new)
        AuditService.log(approver, "authorize_lifecycle" if approve else "reject_lifecycle", proposal,
                         before={"status": L.PROPOSED}, after={"status": new}, reason=reason)
        word = "approved" if approve else f"rejected ({reason})"
        notify_many(_users(RoleName.CUSTODIAN, proposal.asset.owner_department_id),
                    f"The {proposal.action.lower()} of “{proposal.asset.name}” was {word}.", proposal.asset)
        proposal.refresh_from_db()
        return proposal

    @staticmethod
    @transaction.atomic
    def execute(custodian, proposal, evidence):
        evidence = (evidence or "").strip()
        if not evidence:
            raise MaintenanceError("Add the evidence, for example the charity's receipt or the recycler's "
                                   "collection note number.")
        proposal = LifecycleAction.objects.select_for_update().select_related("asset").get(pk=proposal.pk)
        if proposal.status != L.APPROVED:
            raise MaintenanceError("Only an approved proposal can be carried out.")
        asset = proposal.asset
        if asset.status not in RETIRABLE:
            raise MaintenanceError(f"“{asset.name}” is {asset.get_status_display()} now; it can only be retired "
                                   f"when Available, In use or Under maintenance.")
        StateService.move(custodian, asset, A.RETIRED, action="retire_asset",
                          reason=f"{proposal.action} carried out: {evidence}")
        for fault in MaintenanceRecord.objects.filter(asset=asset, status__in=OPEN_FAULTS):
            MaintenanceRecord.objects.filter(pk=fault.pk).update(status=M.CANCELLED)
            AuditService.log(custodian, "close_fault", fault, before={"status": fault.status},
                             after={"status": M.CANCELLED}, reason=f"item retired ({proposal.action.lower()})")
        LifecycleAction.objects.filter(pk=proposal.pk).update(status=L.EXECUTED, execution_evidence=evidence)
        AuditService.log(custodian, "execute_lifecycle", proposal, before={"status": L.APPROVED},
                         after={"status": L.EXECUTED, "evidence": evidence})
        proposal.refresh_from_db()
        return proposal

    @staticmethod
    @transaction.atomic
    def cancel(custodian, proposal, reason):
        reason = (reason or "").strip()
        proposal = LifecycleAction.objects.select_for_update().get(pk=proposal.pk)
        if proposal.status not in OPEN_PROPOSALS:
            raise MaintenanceError(f"This proposal is already {proposal.get_status_display()}.")
        if not reason:
            raise MaintenanceError("Give a reason for cancelling.")
        LifecycleAction.objects.filter(pk=proposal.pk).update(status=L.CANCELLED)
        AuditService.log(custodian, "cancel_lifecycle", proposal, before={"status": proposal.status},
                         after={"status": L.CANCELLED}, reason=reason)
        proposal.refresh_from_db()
        return proposal
