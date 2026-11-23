"""AI #3 pages: ask for advice on one asset, then follow or dismiss it (custodian of the owner department)."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.decorators import permission_required
from accounts.permissions import Action
from assets.models import Asset
from circular_campus.choices import AssetStatus

from .advice import answer_advice, load_advice, recommend_action


def _asset(request, pk, **_):  # also used as the permission loader, which passes record_id
    return get_object_or_404(Asset, pk=pk)


def _back(asset, record_id=None):
    url = reverse("assets:detail", args=[asset.pk])
    return redirect(f"{url}?advice={record_id}#advice" if record_id else f"{url}#advice")


@require_POST
@permission_required(Action.REGISTER_ASSET, record=_asset)
def ask(request, pk):
    asset = _asset(request, pk)
    if asset.status in (AssetStatus.RETIRED, AssetStatus.DRAFT):
        messages.info(request, f"This item is {asset.get_status_display()}, so there is nothing to advise on.")
        return _back(asset)
    advice = recommend_action(asset)
    return _back(asset, advice.record_id)


@require_POST
@permission_required(Action.REGISTER_ASSET, record=_asset)
def answer(request, pk, record_id):
    asset = _asset(request, pk)
    advice = load_advice(record_id, asset)
    accept = request.POST.get("decision") == "accept"
    if advice is None or advice.fallback or answer_advice(request.user, record_id, accept) is None:
        messages.warning(request, "This advice was already answered.")
        return _back(asset)
    if accept:
        messages.success(request, f"Advice followed: {advice.action}. Do the step below; the normal rules "
                                  f"and approvals still apply.")
        return _back(asset, record_id)
    messages.info(request, "Advice dismissed. Nothing was changed.")
    return _back(asset)
