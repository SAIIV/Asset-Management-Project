"""C3 Publish and search, C4 Request and track.

  * /catalogue/                 search listed assets (Requester, Custodian, Approver)
  * /catalogue/<id>/            one listed asset, read-only
  * /catalogue/<id>/publish/    custodian of the owning department lists it (POST)
  * /catalogue/<id>/unpublish/  ... or takes it off the catalogue (POST)
  * /requests/                  my requests and their status (Requester)
  * /requests/new/              UC-10 submit (or save a draft); ?asset=<id> pre-ticks a catalogue item
  * /requests/<id>/             one of my requests, with its history
  * /requests/<id>/edit/        UC-11 revise while Draft or Submitted and nothing is reserved
  * /requests/<id>/submit/      Draft -> Submitted (POST)
  * /requests/<id>/cancel/      UC-12 cancel before dispatch (POST)
"""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import permission_required
from accounts.permissions import Action
from assets.models import Asset, Category, Department
from assets.states import IllegalMove, history_of
from circular_campus.choices import Condition, RequestStatus

from .catalogue import CatalogueError, CatalogueService, catalogue, search
from .forms import RequestForm
from .models import ResourceRequest
from .requests import CANCELLABLE, REVISABLE, RequestError, RequestService, candidates_of, eligible_candidates


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


# ------------------------------------------------------------------ C4 Request and track

def _own_request(request, pk):
    """The signed-in requester's own request; anyone else's gives 403 (scope 'own request')."""
    obj = get_object_or_404(ResourceRequest.objects.select_related("specification", "requester"), pk=pk)
    if obj.requester_id != request.user.pk:
        raise PermissionDenied
    return obj


@permission_required(Action.SUBMIT_REQUEST)
def request_list(request):
    """My requests and their status (UC-10 'show request ID and status')."""
    requests = ResourceRequest.objects.filter(requester=request.user).select_related("specification")
    status = request.GET.get("status", "")
    if status:
        requests = requests.filter(status=status)
    page = Paginator(requests.order_by("-id"), 20).get_page(request.GET.get("page"))
    return render(request, "exchange/request_list.html",
                  {"page": page, "status": status, "statuses": RequestStatus.choices})


@permission_required(Action.SUBMIT_REQUEST)
def request_create(request):
    """UC-10 Submit a resource request (Mockup 2). "Request this item" in the catalogue pre-ticks that asset."""
    eligible = eligible_candidates(request.user)
    initial = {}
    asset_id = request.GET.get("asset", "")
    if asset_id.isdigit() and eligible.filter(pk=int(asset_id)).exists():
        initial["candidates"] = [int(asset_id)]
    form = RequestForm(request.POST or None, eligible=eligible, initial=initial)
    if request.method == "POST" and form.is_valid():
        submit = "save_draft" not in request.POST
        try:
            new = RequestService.create(request.user, form.cleaned_data, submit=submit)
        except RequestError as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, f"Request #{new.pk} was {'submitted' if submit else 'saved as a draft'}.")
            return redirect("exchange:request_detail", pk=new.pk)
    return render(request, "exchange/request_form.html", {"form": form, "editing": False})


@permission_required(Action.SUBMIT_REQUEST)
def request_detail(request, pk):
    obj = _own_request(request, pk)
    return render(request, "exchange/request_detail.html", {
        "req": obj,
        "spec": getattr(obj, "specification", None),
        "candidates": candidates_of(obj),
        "reservations": obj.reservations.select_related("asset"),
        "history": history_of("ResourceRequest", obj.pk),
        "can_revise": obj.status in REVISABLE,
        "can_cancel": obj.status in CANCELLABLE,
        "is_draft": obj.status == "Draft",
    })


@permission_required(Action.SUBMIT_REQUEST)
def request_edit(request, pk):
    """UC-11 Revise a pending request."""
    obj = _own_request(request, pk)
    if obj.status not in REVISABLE:
        messages.warning(request, f"This request is {obj.get_status_display()} and can no longer be changed.")
        return redirect("exchange:request_detail", pk=obj.pk)
    spec = getattr(obj, "specification", None)
    initial = {
        "purpose": spec.purpose if spec else "", "quantity": obj.quantity, "required_by": obj.required_by,
        "urgency": obj.urgency, "type": obj.type,
        "mandatory_specs_text": ", ".join(spec.mandatory_specs) if spec else "",
        "preferred_condition": (spec.preferred_condition or "") if spec else "",
        "candidates": [a.pk for a in candidates_of(obj)],
    }
    form = RequestForm(request.POST or None, eligible=eligible_candidates(request.user), initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            RequestService.revise(request.user, obj, form.cleaned_data)
        except RequestError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, "Your changes were saved.")
        return redirect("exchange:request_detail", pk=obj.pk)
    return render(request, "exchange/request_form.html", {"form": form, "editing": True, "req": obj})


@require_POST
@permission_required(Action.SUBMIT_REQUEST)
def request_submit(request, pk):
    obj = _own_request(request, pk)
    try:
        RequestService.submit(request.user, obj)
    except (RequestError, IllegalMove) as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"Request #{obj.pk} was submitted.")
    return redirect("exchange:request_detail", pk=obj.pk)


@require_POST
@permission_required(Action.SUBMIT_REQUEST)
def request_cancel(request, pk):
    """UC-12 Cancel a resource request."""
    obj = _own_request(request, pk)
    try:
        RequestService.cancel(request.user, obj, reason=request.POST.get("reason", "").strip())
    except RequestError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"Request #{obj.pk} was cancelled.")
    return redirect("exchange:request_detail", pk=obj.pk)
