"""C4 Request and track: a requester asks for surplus assets and follows the request.

    RequestService.create(user, data, submit=True)   -> UC-10 Submit a resource request (or save a draft)
    RequestService.revise(user, request, data)       -> UC-11 Revise a pending request
    RequestService.submit(user, request)             -> Draft -> Submitted
    RequestService.cancel(user, request, reason)     -> UC-12 Cancel a resource request

Rules kept here:
  * Quantity is at least 1; "required by" cannot be in the past when the request is submitted.
  * Candidate assets (optional) must be in the catalogue (listed and Available)
    and belong to another department; at most `quantity` of them.
  * A request can be revised only while Draft or Submitted and nothing is reserved
    for it yet (UC-11 alternative "request reserved or changed meanwhile").
  * Cancelling releases any reserved units, so the assets go back to Available
    (Figure 57a "cancel before dispatch releases allocation"). Once a unit is
    dispatched the request can no longer be cancelled.
  * Status changes go through StateService (C6), so they follow Figure 57(a) and are in the history.
  * On submit, the requester and the custodians of the chosen assets get an inbox message (C8).

The requester's chosen candidates are stored as MatchRecommendation rows with
decision Accepted (the requester's choice at gate 2). AI #2 adds its own ranked
rows to the same table later; requester choices are marked with REQUESTER_CHOICE.
"""

from django.db import transaction
from django.utils import timezone

from accounts.services import AuditService
from assets.states import IllegalMove, StateService
from circular_campus.choices import (
    AssetStatus,
    MatchDecision,
    RequestStatus,
    ReservationStatus,
    RoleName,
    TransferStatus,
)
from notifications.services import notify, notify_many

from .catalogue import catalogue
from .models import MatchRecommendation, RequestSpecification, ResourceRequest

REQUESTER_CHOICE = "requester-choice"

#: A request in these states can still be revised (Figure 57a "revise [no reservation]").
REVISABLE = [RequestStatus.DRAFT, RequestStatus.SUBMITTED]
#: ... and in these it can still be cancelled.
CANCELLABLE = [RequestStatus.DRAFT, RequestStatus.SUBMITTED, RequestStatus.UNDER_REVIEW, RequestStatus.APPROVED]

REQUEST_FIELDS = ["quantity", "urgency", "required_by", "type"]


class RequestError(Exception):
    """The request was refused; the message is shown to the user."""


def candidates_of(request):
    """The assets the requester chose, in the order chosen."""
    rows = request.matches.filter(model_version=REQUESTER_CHOICE).select_related("asset", "asset__owner_department")
    return [row.asset for row in rows.order_by("rank_position")]


def eligible_candidates(user):
    """Catalogue assets this user may ask for: listed, Available, from another department."""
    return catalogue().exclude(owner_department_id=user.department_id).order_by("name", "id")


def snapshot(request):
    spec = getattr(request, "specification", None)
    return {
        "quantity": request.quantity, "urgency": request.urgency, "required_by": str(request.required_by),
        "type": request.type, "status": request.status, "version": request.version,
        "purpose": spec.purpose if spec else "", "mandatory_specs": spec.mandatory_specs if spec else [],
        "preferred_condition": spec.preferred_condition if spec else None,
        "candidates": [asset.pk for asset in candidates_of(request)],
    }


def _check(user, data, submitting):
    if user.department_id is None:
        raise RequestError("Your account has no department, so you cannot make requests.")
    if data["quantity"] < 1:
        raise RequestError("Quantity must be at least 1.")
    if submitting and data["required_by"] < timezone.localdate():
        raise RequestError("The required-by date cannot be in the past.")
    candidates = list(data.get("candidates") or [])
    if len(candidates) > data["quantity"]:
        raise RequestError(f"You chose {len(candidates)} assets but asked for {data['quantity']}. "
                           f"Choose at most {data['quantity']}.")
    allowed = set(eligible_candidates(user).values_list("pk", flat=True))
    for asset in candidates:
        if asset.pk not in allowed:
            raise RequestError(f"“{asset.name}” is no longer available in the catalogue. Please choose again.")
    return candidates


def _save_candidates(request, candidates):
    request.matches.filter(model_version=REQUESTER_CHOICE).delete()
    for position, asset in enumerate(candidates, start=1):
        MatchRecommendation.objects.create(
            request=request, asset=asset, score=0, rank_position=position, model_version=REQUESTER_CHOICE,
            explanation="Chosen by the requester from the catalogue", decision=MatchDecision.ACCEPTED,
        )


def _custodians_of(assets):
    from accounts.models import User
    departments = {asset.owner_department_id for asset in assets}
    return User.objects.filter(department_id__in=departments, roles__name=RoleName.CUSTODIAN, is_active=True).distinct()


def _announce_submission(user, request):
    notify(user, f"Your request #{request.pk} was submitted. You will get a message when it is reviewed.", request)
    candidates = candidates_of(request)
    if candidates:
        names = ", ".join(asset.name for asset in candidates)
        notify_many(_custodians_of(candidates),
                    f"New request #{request.pk} from {user.department} asks for: {names}.", request)


class RequestService:
    @staticmethod
    @transaction.atomic
    def create(user, data, submit=True):
        """UC-10: save the request as Draft, then submit it unless it is only a draft."""
        candidates = _check(user, data, submitting=submit)
        request = ResourceRequest.objects.create(requester=user, **{f: data[f] for f in REQUEST_FIELDS})
        RequestSpecification.objects.create(
            request=request, purpose=data["purpose"], mandatory_specs=data.get("mandatory_specs") or [],
            preferred_condition=data.get("preferred_condition") or None,
        )
        _save_candidates(request, candidates)
        AuditService.log(user, "create_request", request, after=snapshot(request))
        if submit:
            StateService.move(user, request, RequestStatus.SUBMITTED, action="submit_request")
            _announce_submission(user, request)
        return request

    @staticmethod
    @transaction.atomic
    def submit(user, request):
        request = ResourceRequest.objects.select_for_update().get(pk=request.pk)
        data = {f: getattr(request, f) for f in REQUEST_FIELDS}
        data["candidates"] = candidates_of(request)
        _check(user, data, submitting=True)
        StateService.move(user, request, RequestStatus.SUBMITTED, action="submit_request")
        _announce_submission(user, request)
        return request

    @staticmethod
    @transaction.atomic
    def revise(user, request, data):
        """UC-11: change a Draft or Submitted request that has nothing reserved yet."""
        request = ResourceRequest.objects.select_for_update().get(pk=request.pk)
        if request.status not in REVISABLE:
            raise RequestError(f"This request is {request.get_status_display()} and can no longer be changed.")
        if request.reservations.filter(status=ReservationStatus.ACTIVE).exists():
            raise RequestError("Units were reserved for this request meanwhile, so it can no longer be changed.")
        candidates = _check(user, data, submitting=request.status == RequestStatus.SUBMITTED)
        before = snapshot(request)
        for field in REQUEST_FIELDS:
            setattr(request, field, data[field])
        request.save(update_fields=REQUEST_FIELDS)
        RequestSpecification.objects.update_or_create(request=request, defaults={
            "purpose": data["purpose"], "mandatory_specs": data.get("mandatory_specs") or [],
            "preferred_condition": data.get("preferred_condition") or None,
        })
        _save_candidates(request, candidates)
        request.refresh_from_db()
        after = snapshot(request)
        changed = [key for key in after if after[key] != before[key]]
        AuditService.log(user, "revise_request", request,
                         before={k: before[k] for k in changed}, after={k: after[k] for k in changed})
        return request

    @staticmethod
    @transaction.atomic
    def cancel(user, request, reason=""):
        """UC-12: cancel before dispatch; reserved units are released and go back to Available."""
        request = ResourceRequest.objects.select_for_update().get(pk=request.pk)
        if request.status not in CANCELLABLE:
            raise RequestError(f"This request is {request.get_status_display()} and cannot be cancelled.")
        if request.transfers.filter(status__in=[TransferStatus.DISPATCHED, TransferStatus.DISPUTED,
                                                TransferStatus.RECEIVED]).exists():
            raise RequestError("Units were already dispatched, so the request cannot be cancelled now.")
        for reservation in request.reservations.filter(status=ReservationStatus.ACTIVE).select_related("asset"):
            StateService.move(user, reservation, ReservationStatus.RELEASED, action="release_reservation",
                              reason="Request cancelled")
            reservation.released_at = timezone.now()
            reservation.save(update_fields=["released_at"])
            if reservation.asset.status == AssetStatus.RESERVED:
                StateService.move(user, reservation.asset, AssetStatus.AVAILABLE, action="release_asset",
                                  reason=f"Request #{request.pk} cancelled")
        for transfer in request.transfers.filter(status__in=[TransferStatus.DRAFT, TransferStatus.SCHEDULED]):
            StateService.move(user, transfer, TransferStatus.CANCELLED, reason="Request cancelled")
        try:
            StateService.move(user, request, RequestStatus.CANCELLED, action="cancel_request",
                              reason=reason or "Cancelled by the requester")
        except IllegalMove as error:
            raise RequestError(str(error)) from error
        notify_many(_custodians_of(candidates_of(request)),
                    f"Request #{request.pk} was cancelled by the requester.", request)
        return request
