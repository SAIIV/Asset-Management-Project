"""C5 Approve and transfer: reserve, approve, release and receive (UC-13 to UC-17).

    TransferService.reserve(custodian, request, assets)             UC-13 Reserve eligible assets
    TransferService.cannot_supply(custodian, request, reason)       UC-13 alternative: tell the requester
    TransferService.decide(approver, request, decision, reason)     UC-14 Approve / reject / return
    TransferService.release(custodian, transfer)                    UC-16 Release units
    TransferService.receive(requester, transfer, condition, ok, note)  UC-17 Confirm receipt

The rules (Phase 6 plan "no self-approval; receiver confirms; owner and
department change; the last unit cannot go to two people"):
  * Reserve: every chosen unit must still be Available and belong to the
    custodian's department, or nothing is reserved (units are locked together
    or not at all, Figure 58b). The database also allows only one Active
    reservation per asset, so the last unit can never be held for two requests.
    When the full quantity is reserved the request goes to UnderReview and the
    approvers are told.
  * Decide: the approver is never the requester (BR-02). Approve creates one
    Scheduled transfer per reserved unit. Reject or return releases the units.
  * Release: Scheduled -> Dispatched, asset Reserved -> InTransit. Custody does not move yet.
  * Receive: only the requester confirms. All good -> Received, asset InUse and
    owned by the requester's department; when every unit is received the request
    is Fulfilled. A problem -> Disputed and the previous custody is kept (BR-07);
    a later confirmation resolves it.
Every status change goes through StateService (C6) and every step sends inbox messages (C8).
"""

from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.services import AuditService
from assets.models import Asset
from assets.states import StateService
from circular_campus.choices import (
    ApprovalDecision,
    AssetStatus,
    RequestStatus,
    ReservationStatus,
    RoleName,
    TransferStatus,
)
from exchange.models import ResourceRequest
from notifications.services import notify, notify_many

from .models import Approval, Reservation, Transfer


class TransferError(Exception):
    """The step was refused; the message is shown to the user."""


def _users_with_role(role, department_id=None):
    from accounts.models import User
    users = User.objects.filter(roles__name=role, is_active=True)
    if department_id is not None:
        users = users.filter(department_id=department_id)
    return users.distinct()


def active_reservations(request):
    return request.reservations.filter(status=ReservationStatus.ACTIVE).select_related("asset")


def still_needed(request):
    return max(request.quantity - active_reservations(request).count(), 0)


def _release_reservations(user, request, reason):
    for reservation in active_reservations(request):
        StateService.move(user, reservation, ReservationStatus.RELEASED, action="release_reservation", reason=reason)
        Reservation.objects.filter(pk=reservation.pk).update(released_at=timezone.now())
        if reservation.asset.status == AssetStatus.RESERVED:
            StateService.move(user, reservation.asset, AssetStatus.AVAILABLE, action="release_asset",
                              reason=f"Request #{request.pk}: {reason}")


class TransferService:
    @staticmethod
    @transaction.atomic
    def reserve(custodian, request, assets):
        """UC-13: hold the chosen units of the custodian's department for this request."""
        request = ResourceRequest.objects.select_for_update().get(pk=request.pk)
        if request.status != RequestStatus.SUBMITTED:
            raise TransferError(f"Request #{request.pk} is {request.get_status_display()}; units can only be "
                                f"reserved for a Submitted request.")
        assets = list(assets)
        if not assets:
            raise TransferError("Choose at least one unit to reserve.")
        needed = still_needed(request)
        if len(assets) > needed:
            raise TransferError(f"The request needs {needed} more unit(s); you chose {len(assets)}.")
        locked = list(Asset.objects.select_for_update().filter(pk__in=[a.pk for a in assets]))
        for asset in locked:
            if asset.owner_department_id != custodian.department_id:
                raise TransferError(f"“{asset.name}” belongs to another department.")
            if asset.status != AssetStatus.AVAILABLE:
                raise TransferError(f"“{asset.name}” is {asset.get_status_display()} now, so nothing was reserved. "
                                    f"Please choose again.")
        try:
            with transaction.atomic():
                for asset in locked:
                    Reservation.objects.create(request=request, asset=asset)
                    StateService.move(custodian, asset, AssetStatus.RESERVED, action="reserve_asset",
                                      reason=f"Reserved for request #{request.pk}")
        except IntegrityError as error:
            raise TransferError("One of these units was reserved for another request a moment ago. "
                                "Nothing was reserved; please choose again.") from error
        if still_needed(request) == 0:
            StateService.move(custodian, request, RequestStatus.UNDER_REVIEW, action="reserve_request",
                              reason="All units reserved")
            notify_many([u for u in _users_with_role(RoleName.APPROVER) if u.pk != request.requester_id],
                        f"Request #{request.pk} has all units reserved and is waiting for approval.", request)
        notify(request.requester, f"{len(locked)} unit(s) were reserved for your request #{request.pk}.", request)
        return request

    @staticmethod
    @transaction.atomic
    def decide(approver, request, decision, reason=""):
        """UC-14: approve, reject or return a request that is UnderReview."""
        request = ResourceRequest.objects.select_for_update().get(pk=request.pk)
        if request.requester_id == approver.pk:
            raise TransferError("You cannot approve your own request (BR-02).")
        if request.status != RequestStatus.UNDER_REVIEW:
            raise TransferError(f"Request #{request.pk} is {request.get_status_display()}, not waiting for approval.")
        if decision not in (ApprovalDecision.APPROVED, ApprovalDecision.REJECTED,
                            ApprovalDecision.RETURNED_FOR_CORRECTION):
            raise TransferError("Unknown decision.")
        if decision != ApprovalDecision.APPROVED and not reason.strip():
            raise TransferError("Please give a reason when you reject or return a request.")
        approval = Approval.objects.create(request=request, approver=approver)
        StateService.move(approver, approval, decision, action="decide_approval", reason=reason)
        Approval.objects.filter(pk=approval.pk).update(reason=reason, decided_at=timezone.now())

        if decision == ApprovalDecision.APPROVED:
            StateService.move(approver, request, RequestStatus.APPROVED, action="approve_request", reason=reason)
            for reservation in active_reservations(request):
                transfer = Transfer.objects.create(asset=reservation.asset, request=request, approver=approver,
                                                   type=request.type)
                StateService.move(approver, transfer, TransferStatus.SCHEDULED, action="schedule_transfer")
                notify_many(_users_with_role(RoleName.CUSTODIAN, reservation.asset.owner_department_id),
                            f"Request #{request.pk} was approved. Please release “{reservation.asset.name}”.",
                            transfer)
            notify(request.requester, f"Your request #{request.pk} was approved.", request)
        else:
            target = RequestStatus.REJECTED if decision == ApprovalDecision.REJECTED else RequestStatus.SUBMITTED
            word = "rejected" if decision == ApprovalDecision.REJECTED else "returned for correction"
            departments = {r.asset.owner_department_id for r in active_reservations(request)}
            _release_reservations(approver, request, f"request {word}")
            StateService.move(approver, request, target, action=f"{decision.lower()}_request", reason=reason)
            notify(request.requester, f"Your request #{request.pk} was {word}: {reason}", request)
            for department in departments:
                notify_many(_users_with_role(RoleName.CUSTODIAN, department),
                            f"Request #{request.pk} was {word}; its reserved units are Available again.", request)
        return approval

    @staticmethod
    @transaction.atomic
    def cannot_supply(custodian, request, reason):
        """UC-13 alternative: the custodian's department cannot supply this request.

        The custodian does not reject the request (only an independent approver can,
        BR-02): it stays Submitted, nothing is reserved, and the requester is told why
        so they can revise or cancel it (UC-11, UC-12). Other departments can still supply it.
        """
        reason = (reason or "").strip()
        if not reason:
            raise TransferError("Say why your department cannot supply it, so the requester knows what to change.")
        request = ResourceRequest.objects.select_for_update().get(pk=request.pk)
        if request.status != RequestStatus.SUBMITTED:
            raise TransferError(f"Request #{request.pk} is {request.get_status_display()}, so there is nothing "
                                f"to turn down any more.")
        department = custodian.department
        AuditService.log(custodian, "cannot_supply", request, reason=reason,
                         after={"department": department.name if department else ""})
        notify(request.requester, f"{department or 'A department'} cannot supply request #{request.pk}: {reason}. "
                                  f"The request stays open; you can change or cancel it.", request)
        return request

    @staticmethod
    @transaction.atomic
    def release(custodian, transfer):

        """UC-16: hand the unit over. Custody stays with the sender until the receiver confirms."""
        transfer = Transfer.objects.select_for_update().select_related("asset", "request").get(pk=transfer.pk)
        if transfer.status != TransferStatus.SCHEDULED:
            raise TransferError(f"This transfer is {transfer.get_status_display()} and cannot be released.")
        StateService.move(custodian, transfer, TransferStatus.DISPATCHED, action="release_transfer")
        Transfer.objects.filter(pk=transfer.pk).update(released_at=timezone.now())
        reservation = transfer.request.reservations.filter(asset=transfer.asset, status=ReservationStatus.ACTIVE).first()
        if reservation:
            StateService.move(custodian, reservation, ReservationStatus.CONSUMED, action="consume_reservation")
        StateService.move(custodian, transfer.asset, AssetStatus.IN_TRANSIT, action="release_asset",
                          reason=f"Released for request #{transfer.request_id}")
        notify(transfer.request.requester,
               f"“{transfer.asset.name}” is on its way for request #{transfer.request_id}. "
               f"Please confirm when you receive it.", transfer.request)
        transfer.refresh_from_db()
        return transfer

    @staticmethod
    @transaction.atomic
    def receive(requester, transfer, condition, all_ok=True, note=""):
        """UC-17: the receiver confirms. Only now do owner and department change (BR-07)."""
        transfer = Transfer.objects.select_for_update().select_related("asset", "request").get(pk=transfer.pk)
        request = transfer.request
        if request.requester_id != requester.pk:
            raise TransferError("Only the person who made the request can confirm receipt.")
        if transfer.status not in (TransferStatus.DISPATCHED, TransferStatus.DISPUTED):
            raise TransferError(f"This transfer is {transfer.get_status_display()}; there is nothing to receive.")
        sender_department = transfer.asset.owner_department_id
        custodians = _users_with_role(RoleName.CUSTODIAN, sender_department)
        Transfer.objects.filter(pk=transfer.pk).update(condition_on_receipt=condition)

        if not all_ok:
            if transfer.status == TransferStatus.DISPUTED:
                raise TransferError("This transfer is already disputed.")
            StateService.move(requester, transfer, TransferStatus.DISPUTED, action="dispute_transfer",
                              reason=note or "Mismatch or damage reported on receipt")
            notify_many(custodians, f"Request #{request.pk}: the receiver reported a problem with "
                                    f"“{transfer.asset.name}”: {note or 'no details'}", transfer)
            transfer.refresh_from_db()
            return transfer

        Transfer.objects.filter(pk=transfer.pk).update(received_at=timezone.now())
        StateService.move(requester, transfer, TransferStatus.RECEIVED, action="receive_transfer",
                          reason=note or ("Resolved and received" if transfer.status == TransferStatus.DISPUTED else ""))
        asset = transfer.asset
        StateService.move(requester, asset, AssetStatus.IN_USE, action="receive_asset",
                          reason=f"Received for request #{request.pk}")
        before = {"owner_department": asset.owner_department_id, "condition": asset.condition}
        Asset.objects.filter(pk=asset.pk).update(owner_department_id=requester.department_id, condition=condition)
        AuditService.log(requester, "change_custody", record_type="Asset", record_id=asset.pk, before=before,
                         after={"owner_department": requester.department_id, "condition": condition},
                         reason=f"Transfer #{transfer.pk} received")
        notify_many(custodians, f"“{asset.name}” was received by {requester.department} (request #{request.pk}).",
                    transfer)
        if not request.transfers.exclude(status__in=[TransferStatus.RECEIVED, TransferStatus.CANCELLED]).exists():
            StateService.move(requester, request, RequestStatus.FULFILLED, action="fulfil_request",
                              reason="All units received")
            notify(requester, f"Request #{request.pk} is complete: every unit was received.", request)
        transfer.refresh_from_db()
        return transfer

