"""Maintenance and lifecycle pages (UC-19 to UC-25). The rules are in maintenance.py; views only check
the access matrix for the record, call the service and show the result."""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.decorators import permission_required
from accounts.models import AuditLog
from accounts.permissions import Action, can
from circular_campus.choices import AssetStatus as A, LifecycleActionType, LifecycleStatus as L

from .maintenance import (
    OPEN_FAULTS,
    LifecycleService,
    MaintenanceError,
    MaintenanceService,
    reported_by,
    with_proposer,
)
from .models import Asset, LifecycleAction, MaintenanceRecord
from .states import IllegalMove


def _check(user, action, record):
    if not can(user, action, record):
        raise PermissionDenied


def _run(request, step, done, use_next=True):
    try:
        step()
    except (MaintenanceError, IllegalMove) as error:
        messages.error(request, str(error))
    else:
        messages.success(request, done)
    target = request.POST.get("next", "") if use_next else ""
    if target and url_has_allowed_host_and_scheme(target, {request.get_host()}, request.is_secure()):
        return redirect(target)
    return redirect("maintenance:list")


def _maintenance_allowed(user):
    return any(can(user, a) for a in (Action.REPORT_FAULT, Action.PROPOSE_LIFECYCLE, Action.AUTHORIZE_LIFECYCLE))


def maintenance_list(request):
    if not request.user.is_authenticated:
        return redirect("login")
    user = request.user
    if not _maintenance_allowed(user):
        raise PermissionDenied
    dept = user.department_id
    context = {"kinds": LifecycleActionType.choices}
    if can(user, Action.REPORT_FAULT):
        context["my_items"] = (Asset.objects.filter(owner_department_id=dept)
                               .exclude(status__in=[A.RETIRED, A.DRAFT]).order_by("name"))
        mine = AuditLog.objects.filter(user=user, action="report_fault").values_list("record_id", flat=True)
        context["reported"] = (MaintenanceRecord.objects.filter(pk__in=mine).select_related("asset")
                               .order_by("-reported_at")[:10])
    if can(user, Action.REGISTER_ASSET):
        faults = MaintenanceRecord.objects.filter(asset__owner_department_id=dept).select_related("asset")
        context["open_faults"] = faults.filter(status__in=OPEN_FAULTS).order_by("reported_at")
        context["closed_faults"] = faults.exclude(status__in=OPEN_FAULTS).order_by("-reported_at")[:8]
        for record in context["open_faults"]:
            record.reporter = reported_by(record)
    if can(user, Action.PROPOSE_LIFECYCLE):
        context["our_proposals"] = (LifecycleAction.objects.filter(asset__owner_department_id=dept)
                                    .select_related("asset").order_by("-pk")[:15])
    if can(user, Action.AUTHORIZE_LIFECYCLE):
        waiting = [with_proposer(p) for p in LifecycleAction.objects.filter(status=L.PROPOSED)
                   .select_related("asset__owner_department").order_by("pk")]
        context["to_decide"] = [p for p in waiting if p.proposer_id != user.pk]
    return render(request, "assets/maintenance.html", context)


@require_POST
@permission_required(Action.REPORT_FAULT)
def report_fault(request):
    asset = get_object_or_404(Asset, pk=request.POST.get("asset") or 0)
    if asset.owner_department_id != request.user.department_id and not asset.is_listed:
        raise PermissionDenied  # you can report items you hold, or items you can see in the catalogue
    # A report takes the item off the catalogue, so someone from another department cannot go back to its
    # catalogue page; they see their report under "Faults I reported" instead.
    own = asset.owner_department_id == request.user.department_id and "/catalogue/" not in request.POST.get("next", "")
    return _run(request, lambda: MaintenanceService.report_fault(request.user, asset, request.POST.get("description")),
                "Fault reported. The custodian of the item has been told, and it is off the catalogue until "
                "it is checked.", use_next=own)


def _record(request, pk):
    record = get_object_or_404(MaintenanceRecord.objects.select_related("asset"), pk=pk)
    _check(request.user, Action.REGISTER_ASSET, record.asset)  # custodian of the owner department
    return record


@require_POST
def start_repair(request, pk):
    record = _record(request, pk)
    return _run(request, lambda: MaintenanceService.start_repair(request.user, record),
                f"Repair started. “{record.asset.name}” is now Under maintenance and off the catalogue.")


@require_POST
def finish_repair(request, pk):
    record = _record(request, pk)
    return _run(request, lambda: MaintenanceService.finish_repair(request.user, record, request.POST.get("cost", ""),
                                                                  request.POST.get("note", "")),
                f"Repair finished. “{record.asset.name}” is back in use.")


@require_POST
def close_fault(request, pk):
    record = _record(request, pk)
    return _run(request, lambda: MaintenanceService.cancel(request.user, record, request.POST.get("reason")),
                "The fault was closed without a repair.")


@require_POST
def propose(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    _check(request.user, Action.PROPOSE_LIFECYCLE, asset)
    return _run(request, lambda: LifecycleService.propose(request.user, asset, request.POST.get("kind"),
                                                          request.POST.get("reason")),
                "Proposal sent to the approvers. The item is off the catalogue while it is open.")


def _proposal(request, pk, action):
    proposal = with_proposer(get_object_or_404(LifecycleAction.objects.select_related("asset"), pk=pk))
    _check(request.user, action, proposal if action == Action.AUTHORIZE_LIFECYCLE else proposal.asset)
    return proposal


@require_POST
def decide(request, pk):
    proposal = _proposal(request, pk, Action.AUTHORIZE_LIFECYCLE)
    approve = request.POST.get("decision") == "approve"
    return _run(request, lambda: LifecycleService.decide(request.user, proposal, approve, request.POST.get("reason")),
                "Approved. The custodian can now carry it out." if approve else "Rejected. The custodian was told why.")


@require_POST
def execute(request, pk):
    proposal = _proposal(request, pk, Action.PROPOSE_LIFECYCLE)
    return _run(request, lambda: LifecycleService.execute(request.user, proposal, request.POST.get("evidence")),
                f"Done. “{proposal.asset.name}” is now Retired.")


@require_POST
def cancel_proposal(request, pk):
    proposal = _proposal(request, pk, Action.PROPOSE_LIFECYCLE)
    return _run(request, lambda: LifecycleService.cancel(request.user, proposal, request.POST.get("reason")),
                "The proposal was cancelled.")
