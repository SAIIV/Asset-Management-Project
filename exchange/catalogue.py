"""C3 Publish and search: the catalogue of surplus assets other departments can ask for.

    CatalogueService.publish(user, asset)     -> list an Available asset (UC-06 / UC-07)
    CatalogueService.unpublish(user, asset)   -> take it off the catalogue
    search(query, category, condition, department)   -> UC-08 Search listed assets

Rules kept here:
  * Only an Available asset can be listed (Figure 56: "Available - listed when
    published"). Draft, Reserved, InTransit, InUse, UnderMaintenance and
    Retired assets never show in the catalogue, even if is_listed was left on.
  * Publishing and unpublishing each write one audit-log row.
  * Search filters by keyword (name, description, category, tags), category,
    condition and owning department, and only ever returns listed + Available assets.
"""

from django.db import transaction
from django.db.models import Q

from accounts.services import AuditService
from assets.models import Asset
from circular_campus.choices import AssetStatus


class CatalogueError(Exception):
    """The publish or unpublish was refused; the message is shown to the user."""


def catalogue():
    """Every asset a requester may see right now: listed and Available."""
    return (Asset.objects.filter(is_listed=True, status=AssetStatus.AVAILABLE)
            .select_related("category", "owner_department"))


def search(query="", category=None, condition="", department=None):
    """UC-08: filter the catalogue. Each word of the keyword must appear somewhere."""
    assets = catalogue()
    for word in query.split():
        assets = assets.filter(
            Q(name__icontains=word) | Q(description__icontains=word) | Q(category__name__icontains=word)
            | Q(tags__contains=[word]) | Q(tags__contains=[word.lower()])
        )
    if category:
        assets = assets.filter(Q(category_id=category) | Q(category__parent_category_id=category))
    if condition:
        assets = assets.filter(condition=condition)
    if department:
        assets = assets.filter(owner_department_id=department)
    return assets.distinct().order_by("name", "id")


class CatalogueService:
    @staticmethod
    @transaction.atomic
    def publish(user, asset):
        asset = Asset.objects.select_for_update().get(pk=asset.pk)
        if asset.status != AssetStatus.AVAILABLE:
            raise CatalogueError(
                f"Only an Available asset can be published. This one is {asset.get_status_display()}."
            )
        if asset.is_listed:
            raise CatalogueError("This asset is already in the catalogue.")
        Asset.objects.filter(pk=asset.pk).update(is_listed=True)
        AuditService.log(user, "publish_asset", record_type="Asset", record_id=asset.pk,
                         before={"is_listed": False}, after={"is_listed": True})
        asset.refresh_from_db()
        return asset

    @staticmethod
    @transaction.atomic
    def unpublish(user, asset, reason=""):
        asset = Asset.objects.select_for_update().get(pk=asset.pk)
        if not asset.is_listed:
            raise CatalogueError("This asset is not in the catalogue.")
        Asset.objects.filter(pk=asset.pk).update(is_listed=False)
        AuditService.log(user, "unpublish_asset", record_type="Asset", record_id=asset.pk,
                         before={"is_listed": True}, after={"is_listed": False}, reason=reason)
        asset.refresh_from_db()
        return asset
