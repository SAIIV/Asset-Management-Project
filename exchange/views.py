"""C3 Publish and search.

  * /catalogue/                 search listed assets (Requester, Custodian, Approver)
  * /catalogue/<id>/            one listed asset, read-only
  * /catalogue/<id>/publish/    custodian of the owning department lists it (POST)
  * /catalogue/<id>/unpublish/  ... or takes it off the catalogue (POST)
"""

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import permission_required
from accounts.permissions import Action
from assets.models import Asset, Category, Department
from circular_campus.choices import Condition

from .catalogue import CatalogueError, CatalogueService, catalogue, search


def _load_asset(request, pk):
    return get_object_or_404(Asset.objects.select_related("category", "owner_department"), pk=pk)


def _int_or_none(value):
    return int(value) if value and value.isdigit() else None


@permission_required(Action.SEARCH_ASSETS)
def catalogue_list(request):
    """UC-08 Search listed assets: keyword, category, condition and department."""
    query = request.GET.get("q", "").strip()
    category = _int_or_none(request.GET.get("category", ""))
    condition = request.GET.get("condition", "")
    if condition not in Condition.values:
        condition = ""
    department = _int_or_none(request.GET.get("department", ""))
    results = search(query, category, condition, department)
    page = Paginator(results, 20).get_page(request.GET.get("page"))
    filters = request.GET.copy()
    filters.pop("page", None)
    return render(request, "exchange/catalogue_list.html", {
        "page": page,
        "query": query, "category": category, "condition": condition, "department": department,
        "categories": Category.objects.all(), "conditions": Condition.choices,
        "departments": Department.objects.all(),
        "filters": filters.urlencode(),
        "filtered": bool(query or category or condition or department),
    })


@permission_required(Action.SEARCH_ASSETS)
def catalogue_detail(request, pk):
    """One listed asset. An asset that is not listed and Available is not shown (404)."""
    asset = catalogue().filter(pk=pk).first()
    if asset is None:
        raise Http404("This asset is not in the catalogue.")
    return render(request, "exchange/catalogue_detail.html", {"asset": asset})


@require_POST
@permission_required(Action.REGISTER_ASSET, record=_load_asset)
def publish(request, pk):
    """UC-07 Publish surplus: only the custodian of the owning department."""
    try:
        CatalogueService.publish(request.user, _load_asset(request, pk))
    except CatalogueError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "The asset is now in the catalogue, so other departments can find and request it.")
    return redirect("assets:detail", pk=pk)


@require_POST
@permission_required(Action.REGISTER_ASSET, record=_load_asset)
def unpublish(request, pk):
    try:
        CatalogueService.unpublish(request.user, _load_asset(request, pk), reason=request.POST.get("reason", "").strip())
    except CatalogueError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "The asset was taken off the catalogue.")
    return redirect("assets:detail", pk=pk)
