"""C5 Approve and transfer (Mockup 4 and the transfer screens).

Custodian:  /transfers/incoming/                 requests waiting for units
            /transfers/requests/<id>/             UC-13 reserve units of my department
            /transfers/<id>/release/              UC-16 release a scheduled transfer (POST)
Approver:   /transfers/approvals/                 requests waiting for approval
            /transfers/approvals/<id>/            UC-14 approve, reject or return (never your own request)
Requester:  /transfers/<id>/receive/              UC-17 confirm receipt or report a problem (POST)
Everyone:   /transfers/                           transfers I send or receive
            /transfers/go/request/<id>/           opens a request on the right page for your role (inbox links)
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.decorators import permission_required
from accounts.models import AuditLog

from accounts.permissions import Action, can
from assets.maintenance import without_held
from assets.models import Asset
from assets.states import history_of
from circular_campus.choices import ApprovalDecision, AssetStatus, Condition, RequestStatus, TransferStatus
from exchange.models import ResourceRequest
from exchange.requests import candidates_of

from .models import Approval, Transfer
from .services import TransferError, TransferService, active_reservations, still_needed


def _load_request(request, pk):
    return get_object_or_404(ResourceRequest.objects.select_related("requester", "requester__department",
                                                                    "specification"), pk=pk)


def _load_transfer(request, pk):
    return get_object_or_404(Transfer.objects.select_related("asset", "request"), pk=pk)


# ------------------------------------------------------------------ custodian

@permission_required(Action.RESERVE_UNITS)
def incoming(request):
    dept = request.user.department_id
    waiting = (ResourceRequest.objects.filter(status=RequestStatus.SUBMITTED)
               .exclude(requester=request.user).select_related("requester__department", "specification")
               .order_by("required_by", "id"))
    rows = []
    for req in waiting:
        mine = [a for a in candidates_of(req) if a.owner_department_id == dept]
        rows.append({"req": req, "mine": mine, "needed": still_needed(req)})
    rows.sort(key=lambda row: not row["mine"])  # requests naming our items first
    declined = set(AuditLog.objects.filter(action="cannot_supply", user__department_id=dept)
                   .values_list("record_id", flat=True))
    for row in rows:
        row["declined"] = row["req"].pk in declined
    to_release = (Transfer.objects.filter(asset__owner_department_id=dept, status__in=[
        TransferStatus.SCHEDULED, TransferStatus.DISPUTED]).select_related("asset", "request__requester__department"))
    return render(request, "transfers/incoming.html", {"rows": rows, "to_release": to_release})


@require_POST
@permission_required(Action.RESERVE_UNITS)
def cannot_supply(request, pk):
    """UC-13 alternative: tell the requester my department cannot supply it (the request stays open)."""
    req = _load_request(request, pk)
    try:
        TransferService.cannot_supply(request.user, req, request.POST.get("reason", ""))
    except TransferError as error:
        messages.error(request, str(error))
        return redirect("transfers:custodian_request", pk=req.pk)
    messages.success(request, f"The requester was told your department cannot supply request #{req.pk}.")
    return redirect("transfers:incoming")


@permission_required(Action.RESERVE_UNITS)
def custodian_request(request, pk):
    """UC-13 Reserve eligible assets: show the request and the Available units of my department."""
    req = _load_request(request, pk)
    units = without_held(Asset.objects.filter(owner_department_id=request.user.department_id,
                                              status=AssetStatus.AVAILABLE))  # no open fault or retirement
    chosen = {a.pk for a in candidates_of(req)}
    if request.method == "POST":
        ids = [int(i) for i in request.POST.getlist("assets") if i.isdigit()]
        picked = list(units.filter(pk__in=ids)) if ids else []
        if len(picked) != len(ids):
            messages.error(request, "Some of the chosen units are no longer Available, so nothing was reserved.")
        else:
            try:
                TransferService.reserve(request.user, req, picked)
            except TransferError as error:
                messages.error(request, str(error))
            else:
                messages.success(request, f"{len(picked)} unit(s) reserved for request #{req.pk}.")
        return redirect("transfers:custodian_request", pk=req.pk)
    return render(request, "transfers/custodian_request.html", {
        "req": req, "spec": getattr(req, "specification", None), "candidates": candidates_of(req),
        # the requester's choices first, then the newest units
        "units": sorted(units.select_related("category"), key=lambda a: (a.pk not in chosen, -a.pk)),
        "chosen": chosen,
        "needed": still_needed(req), "reservations": active_reservations(req),
        "can_reserve": req.status == RequestStatus.SUBMITTED,
    })


@require_POST
@permission_required(Action.RELEASE_UNITS, record=_load_transfer)
def release(request, pk):
    try:
        TransferService.release(request.user, _load_transfer(request, pk))
    except TransferError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "Released. The asset is in transit until the receiver confirms.")
    return redirect("transfers:list")


# ------------------------------------------------------------------ approver

@permission_required(Action.APPROVE_REQUEST)
def approvals(request):
    waiting = (ResourceRequest.objects.filter(status=RequestStatus.UNDER_REVIEW).exclude(requester=request.user)
               .select_related("requester__department", "specification").order_by("required_by", "id"))
    decided = Approval.objects.filter(approver=request.user).select_related("request").order_by("-decided_at")[:20]
    return render(request, "transfers/approvals.html", {"waiting": waiting, "decided": decided})


@permission_required(Action.APPROVE_REQUEST, record=_load_request)
def approval_detail(request, pk):
    """UC-14 (Mockup 4). The decorator's NOT_OWN scope already refuses your own request (BR-02)."""
    req = _load_request(request, pk)
    if request.method == "POST":
        decision = request.POST.get("decision", "")
        try:
            TransferService.decide(request.user, req, decision, request.POST.get("reason", "").strip())
        except TransferError as error:
            messages.error(request, str(error))
            return redirect("transfers:approval_detail", pk=req.pk)
        messages.success(request, f"Request #{req.pk}: {ApprovalDecision(decision).label}.")
        return redirect("transfers:approvals")
    return render(request, "transfers/approval_detail.html", {
        "req": req, "spec": getattr(req, "specification", None),
        "reservations": active_reservations(req), "history": history_of("ResourceRequest", req.pk),
        "can_decide": req.status == RequestStatus.UNDER_REVIEW,
        "decisions": [ApprovalDecision.APPROVED, ApprovalDecision.REJECTED, ApprovalDecision.RETURNED_FOR_CORRECTION],
    })


# ------------------------------------------------------------------ requester

@require_POST
@permission_required(Action.CONFIRM_RECEIPT, record=_load_transfer)
def receive(request, pk):
    """UC-17 Confirm receipt. "Problem" disputes the transfer and keeps the previous custody."""
    transfer = _load_transfer(request, pk)
    condition = request.POST.get("condition", "")
    if condition not in Condition.values:
        messages.error(request, "Please choose the condition the item arrived in.")
        return redirect("exchange:request_detail", pk=transfer.request_id)
    try:
        TransferService.receive(request.user, transfer, condition,
                                all_ok=request.POST.get("outcome") != "problem",
                                note=request.POST.get("note", "").strip())
    except TransferError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "Thank you, your answer was recorded.")
    return redirect("exchange:request_detail", pk=transfer.request_id)


# ------------------------------------------------------------------ shared

@login_required
def transfer_list(request):
    user = request.user
    mine = Q(request__requester=user)
    if can(user, Action.RELEASE_UNITS):
        mine |= Q(asset__owner_department_id=user.department_id)
    if not (can(user, Action.RELEASE_UNITS) or can(user, Action.CONFIRM_RECEIPT)):
        raise PermissionDenied
    transfers = (Transfer.objects.filter(mine).select_related("asset", "request__requester__department")
                 .order_by("-id")[:100])
    return render(request, "transfers/transfer_list.html", {"transfers": transfers})


@login_required
def open_request(request, pk):
    """Inbox links point here, so each person lands on the page for their role."""
    req = _load_request(request, pk)
    user = request.user
    if req.requester_id == user.pk:
        return redirect("exchange:request_detail", pk=pk)
    if can(user, Action.APPROVE_REQUEST, req) and req.status in (RequestStatus.UNDER_REVIEW, RequestStatus.APPROVED,
                                                                  RequestStatus.REJECTED):
        return redirect("transfers:approval_detail", pk=pk)
    if can(user, Action.RESERVE_UNITS):
        return redirect("transfers:custodian_request", pk=pk)
    raise PermissionDenied


@login_required
def open_transfer(request, pk):
    transfer = get_object_or_404(Transfer, pk=pk)
    if transfer.request.requester_id == request.user.pk:
        return redirect("exchange:request_detail", pk=transfer.request_id)
    return redirect(reverse("transfers:list") + f"#t{pk}")
