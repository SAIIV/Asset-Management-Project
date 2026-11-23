"""C3 Publish and search: the catalogue of surplus assets other departments can ask for.

    CatalogueService.publish(user, asset)     -> list an Available asset (UC-06 / UC-07)
    CatalogueService.unpublish(user, asset)   -> take it off the catalogue
    search(query, category, condition, department)   -> UC-08 Search listed assets

Rules kept here:
  * Only an Available asset can be listed (Figure 56: "Available - listed when
    published"). Draft, Reserved, InTransit, InUse, UnderMaintenance and
    Retired assets never show in the catalogue, even if is_listed was left on.
  * UC-06 step 4: publishing is refused while the asset lacks a field the
    listing needs (description and where to collect it: campus, building, room)
    or is not serviceable (condition Needs repair, or an inspection said no).
    A Draft asset that passes these checks is moved to Available and listed
    in one step (UC-06 step 5). Value and mass stay optional.
  * Publishing and unpublishing each write one audit-log row.
  * Search filters by keyword (name, description, category, tags), category,
    condition and owning department, and only ever returns listed + Available assets.
"""

from django.db import transaction
from django.db.models import Q

from accounts.services import AuditService
from assets.models import Asset
from circular_campus.choices import AssetStatus, Condition

#: Fields a listing must show (UC-06 step 2: specifications, condition, department and location).
LISTING_FIELDS = {"description": "description", "campus": "campus", "building": "building", "room": "room"}


class CatalogueError(Exception):
    """The publish or unpublish was refused; the message is shown to the user."""


def publish_problems(asset):
    """Why this asset cannot be listed yet (empty list = it can). UC-06 step 4."""
    problems = []
    missing = [label for field, label in LISTING_FIELDS.items() if not str(getattr(asset, field) or "").strip()]
    if missing:
        problems.append(f"fill in the {', '.join(missing)} (Edit)")
    if asset.condition == Condition.NEEDS_REPAIR:
        problems.append("it needs repair, so it is not serviceable")
    if asset.serviceability is False:
        problems.append("the last inspection marked it not serviceable")
    if asset.pk:
        from assets.maintenance import hold_reason  # open fault or retirement proposal (UC-19, UC-23)
        held = hold_reason(asset)
        if held:
            problems.append(held)
    return problems


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
        from assets.states import StateService

        asset = Asset.objects.select_for_update().get(pk=asset.pk)
        if asset.status not in (AssetStatus.AVAILABLE, AssetStatus.DRAFT):
            raise CatalogueError(
                f"Only a Draft or Available asset can be published. This one is {asset.get_status_display()}."
            )
        if asset.is_listed:
            raise CatalogueError("This asset is already in the catalogue.")
        problems = publish_problems(asset)
        if problems:
            raise CatalogueError(f"Not published yet: {'; '.join(problems)}.")
        if asset.status == AssetStatus.DRAFT:
            StateService.move(user, asset, AssetStatus.AVAILABLE, action="change_asset_status",
                              reason="Published to the catalogue (UC-06)")

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
