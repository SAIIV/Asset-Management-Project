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
    form = AssetForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            asset = AssetService.register(request.user, form.cleaned_data)
        except AssetEditError as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, f"Asset #{asset.pk} “{asset.name}” was registered.")
            return redirect("assets:detail", pk=asset.pk)
    return render(request, "assets/asset_form.html", {"form": form, "editing": False})


@permission_required(Action.REGISTER_ASSET, record=_load_asset)
def asset_detail(request, pk):
    asset = _load_asset(request, pk)
    kind = kind_of(asset)
    return render(request, "assets/asset_detail.html", {
        "asset": asset,
        "kind_label": KIND_LABELS[kind],
        "details": details_of(asset, kind),
        "locked": asset.status in LOCKED_STATUSES,
    })


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
