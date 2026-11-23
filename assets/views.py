"""C2 Departments and assets: list, register, view and edit assets of your own department.

Every view goes through the C1 access matrix:
  * Action.REGISTER_ASSET is given to the Custodian, scope "own department";
  * views that open one asset pass that asset, so an asset of another
    department gives 403 even if someone types its ID into the address bar.
"""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import permission_required
from accounts.permissions import Action
from circular_campus.choices import AssetStatus

from .forms import AssetForm
from .models import Asset
from .services import KIND_LABELS, LOCKED_STATUSES, AssetEditError, AssetService, details_of, kind_of
from .states import IllegalMove, StateService, custodian_moves, history_of


def _load_asset(request, pk):
    return get_object_or_404(Asset.objects.select_related("category", "owner_department"), pk=pk)


@permission_required(Action.REGISTER_ASSET)
def asset_list(request):
    """All assets of the custodian's department, with a name search and a status filter."""
    assets = Asset.objects.filter(owner_department_id=request.user.department_id).select_related("category")
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if query:
        assets = assets.filter(name__icontains=query)
    if status in AssetStatus.values:
        assets = assets.filter(status=status)
    page = Paginator(assets.order_by("id"), 25).get_page(request.GET.get("page"))
    return render(request, "assets/asset_list.html", {
        "page": page, "query": query, "status": status, "statuses": AssetStatus.choices,
    })


@permission_required(Action.REGISTER_ASSET)
def asset_create(request):
    """UC-04 Register an asset."""
    if request.user.department_id is None:
        raise PermissionDenied
    if request.method == "POST" and "suggest" in request.POST:
        return _suggest_category(request)
    form = AssetForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            asset = AssetService.register(request.user, form.cleaned_data)
        except AssetEditError as error:
            form.add_error(None, str(error))
        else:
            if form.cleaned_data.get("ai_record"):
                from ai.classify import answer
                answer(form.cleaned_data["ai_record"], asset.category_id)  # Accepted or Corrected (Section 13)
            messages.success(request, f"Asset #{asset.pk} “{asset.name}” was registered.")
            return redirect("assets:detail", pk=asset.pk)
    return render(request, "assets/asset_form.html", {"form": form, "editing": False})


def _suggest_category(request):
    """AI #1 (Mockup M1): suggest a category from the name and description.

    The form comes back with everything the custodian typed. A confident
    category is preselected and empty tags/material are filled in; nothing is
    saved until the custodian presses Register.
    """
    from ai.classify import classify_asset

    typed = request.POST.dict()
    typed.pop("csrfmiddlewaretoken", None)
    typed.pop("suggest", None)
    suggestion = classify_asset(typed.get("name", "").strip(), typed.get("description", "").strip())
    if suggestion.category is not None:
        typed["category"] = suggestion.category.pk
    if suggestion.tags and not typed.get("tags_text", "").strip():
        typed["tags_text"] = ", ".join(suggestion.tags)
    if suggestion.material and not typed.get("material", "").strip():
        typed["material"] = suggestion.material
    if not suggestion.fallback:
        typed["ai_record"] = suggestion.record_id
    form = AssetForm(initial=typed)
    return render(request, "assets/asset_form.html", {"form": form, "editing": False, "suggestion": suggestion})



@permission_required(Action.REGISTER_ASSET, record=_load_asset)
def asset_detail(request, pk):
    asset = _load_asset(request, pk)
    kind = kind_of(asset)
    return render(request, "assets/asset_detail.html", {
        "asset": asset,
        "kind_label": KIND_LABELS[kind],
        "details": details_of(asset, kind),
        "locked": asset.status in LOCKED_STATUSES,
        "moves": {} if _repair_in_progress(asset) else custodian_moves(asset),
        "move_choices": [(state, AssetStatus(state).label, event) for state, event in custodian_moves(asset).items()],
        "history": history_of("Asset", asset.pk)[:5],
        **_maintenance_context(request.user, asset),
    })


def _maintenance_context(user, asset):
    """Open fault / open proposal for the "Faults and retirement" card (UC-19, UC-23)."""
    from accounts.permissions import can
    from circular_campus.choices import LifecycleActionType

    from .maintenance import OPEN_FAULTS, OPEN_PROPOSALS, RETIRABLE
    from .models import LifecycleAction, MaintenanceRecord

    return {
        "open_fault": MaintenanceRecord.objects.filter(asset=asset, status__in=OPEN_FAULTS).first(),
        "open_proposal": LifecycleAction.objects.filter(asset=asset, status__in=OPEN_PROPOSALS).first(),
        "can_retire": asset.status in RETIRABLE and can(user, Action.PROPOSE_LIFECYCLE, asset),
        "lifecycle_kinds": LifecycleActionType.choices,
    }


def _repair_in_progress(asset):
    from circular_campus.choices import MaintenanceStatus

    from .models import MaintenanceRecord

    return MaintenanceRecord.objects.filter(asset=asset, status=MaintenanceStatus.IN_PROGRESS).exists()


@permission_required(Action.REGISTER_ASSET, record=_load_asset)
def asset_move(request, pk):
    """C6: change the status by hand, only along an arrow of the asset state diagram (Figure 56)."""
    asset = _load_asset(request, pk)
    if request.method != "POST":
        return redirect("assets:detail", pk=asset.pk)
    new_status = request.POST.get("status", "")
    if not new_status:
        messages.warning(request, "Choose a new status first. Nothing was changed.")
        return redirect("assets:detail", pk=asset.pk)
    # Only the moves offered on the page; reserve, release, receive and retire
    # are made by the request and transfer services, not typed in here.
    if _repair_in_progress(asset):
        messages.error(request, "A repair of this item is in progress. Finish it on the Maintenance page; "
                                "that also sets the status.")
        return redirect("assets:detail", pk=asset.pk)
    if new_status not in custodian_moves(asset):
        messages.error(request, f"An asset that is {asset.get_status_display()} cannot be moved to "
                                f"“{new_status or 'nothing'}” from this page.")
        return redirect("assets:detail", pk=asset.pk)
    if asset.status == AssetStatus.DRAFT and new_status == AssetStatus.AVAILABLE:
        from exchange.catalogue import publish_problems  # "complete fields + serviceable (UC-06)"
        problems = publish_problems(asset)
        if problems:
            messages.error(request, f"Not ready to be Available yet: {'; '.join(problems)}.")
            return redirect("assets:detail", pk=asset.pk)
    try:
        StateService.move(request.user, asset, new_status, reason=request.POST.get("reason", "").strip(),

                          action="change_asset_status")
    except IllegalMove as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"Status changed to {asset.get_status_display()}.")
    return redirect("assets:detail", pk=asset.pk)


@permission_required(Action.REGISTER_ASSET, record=_load_asset)
def asset_history(request, pk):
    """C6: everything that happened to the asset - who did what, when, and why."""
    asset = _load_asset(request, pk)
    page = Paginator(history_of("Asset", asset.pk), 50).get_page(request.GET.get("page"))
    return render(request, "assets/asset_history.html", {"asset": asset, "page": page})



@permission_required(Action.REGISTER_ASSET, record=_load_asset)
def asset_edit(request, pk):
    """UC-05 Update an asset record."""
    asset = _load_asset(request, pk)
    kind = kind_of(asset)
    if asset.status in LOCKED_STATUSES:
        messages.warning(request, f"This asset is {asset.get_status_display()} and cannot be edited right now.")
        return redirect("assets:detail", pk=asset.pk)
    form = AssetForm(request.POST or None, instance=asset, kind=kind, details=details_of(asset, kind))
    if request.method == "POST" and form.is_valid():
        try:
            AssetService.update(request.user, asset, form.cleaned_data)
        except AssetEditError as error:
            messages.error(request, str(error))
            return redirect("assets:detail", pk=asset.pk)
        messages.success(request, "Your changes were saved.")
        return redirect("assets:detail", pk=asset.pk)
    return render(request, "assets/asset_form.html", {"form": form, "editing": True, "asset": asset})
