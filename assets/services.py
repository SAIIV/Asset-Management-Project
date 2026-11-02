"""C2 Departments and assets: the rules for registering and editing an asset.

Views only read the form and call these methods (Phase 6 plan, Section 5).

    AssetService.register(user, cleaned_data)        -> UC-04 Register an asset
    AssetService.update(user, asset, cleaned_data)   -> UC-05 Update an asset record

Rules kept here:
  * The asset always belongs to the custodian's own department.
  * A new asset starts as Draft, Available or InUse. Later status changes
    (reserve, transfer, maintenance, retire) belong to C5/C6, not to this form.
  * An asset that is Reserved, InTransit or Retired cannot be edited
    (UC-05 alternative: "record allocated meanwhile").
  * Two people editing at once: the second save is refused instead of
    silently overwriting the first (the Asset.version column, optimistic locking).
  * Every save writes one row to the audit log with the old and new values.
"""

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import F

from accounts.services import AuditService
from circular_campus.choices import AssetStatus

from .models import Asset, FurnitureAsset, ITAsset, LabEquipment

#: Fields every asset has (columns of the Asset table the custodian fills in).
COMMON_FIELDS = [
    "name", "description", "category", "condition", "campus", "building", "room",
    "purchase_date", "estimated_value_aed", "mass_kg", "tags",
]

#: Asset type -> (model, its extra fields). "general" is a plain Asset row.
KINDS = {
    "it": (ITAsset, ["serial_number"]),
    "lab": (LabEquipment, ["calibration_due"]),
    "furniture": (FurnitureAsset, ["material"]),
    "general": (Asset, []),
}
KIND_LABELS = {"it": "IT equipment", "lab": "Lab equipment", "furniture": "Furniture", "general": "Other"}

#: Status a custodian may give a new asset.
START_STATUSES = [AssetStatus.DRAFT, AssetStatus.AVAILABLE, AssetStatus.IN_USE]

#: While an asset is allocated or retired, its record is frozen.
LOCKED_STATUSES = [AssetStatus.RESERVED, AssetStatus.IN_TRANSIT, AssetStatus.RETIRED]


class AssetEditError(Exception):
    """The edit was refused; the message is shown to the user."""


def kind_of(asset):
    """Which of the three subtypes (or 'general') this asset is."""
    for kind, (model, _) in KINDS.items():
        if model is not Asset and model.objects.filter(pk=asset.pk).exists():
            return kind
    return "general"


def details_of(asset, kind=None):
    """The subtype row (ITAsset, LabEquipment or FurnitureAsset), or None."""
    model = KINDS[kind or kind_of(asset)][0]
    return None if model is Asset else model.objects.get(pk=asset.pk)


def _plain(value):
    """Make a value safe to store as JSON in the audit log."""
    if isinstance(value, (Decimal, date)):
        return str(value)
    if hasattr(value, "pk"):
        return value.pk
    return value


def snapshot(asset):
    """The asset's editable values (plus its subtype fields), for the audit log."""
    kind = kind_of(asset)
    values = {f: _plain(getattr(asset, f)) for f in COMMON_FIELDS}
    values["category"] = asset.category_id
    details = details_of(asset, kind)
    for field in KINDS[kind][1]:
        values[field] = _plain(getattr(details, field))
    values.update(kind=kind, status=asset.status, owner_department=asset.owner_department_id)
    return values


class AssetService:
    @staticmethod
    @transaction.atomic
    def register(user, data):
        """UC-04: create the asset (and its subtype row) in the user's department."""
        if user.department_id is None:
            raise AssetEditError("Your account has no department, so you cannot register assets.")
        if data["status"] not in START_STATUSES:
            raise AssetEditError("A new asset must start as Draft, Available or In use.")
        model, extra = KINDS[data["kind"]]
        values = {f: data[f] for f in COMMON_FIELDS + extra}
        created = model.objects.create(owner_department_id=user.department_id, status=data["status"], **values)
        asset = Asset.objects.get(pk=created.pk)
        AuditService.log(user, "register_asset", asset, record_type="Asset", after=snapshot(asset))
        return asset

    @staticmethod
    @transaction.atomic
    def update(user, asset, data):
        """UC-05: save the changes if nobody else changed or allocated the asset meanwhile."""
        asset = Asset.objects.get(pk=asset.pk)  # the values as stored, before this edit
        before = snapshot(asset)
        kind = before["kind"]
        model, extra = KINDS[kind]
        updated = (
            Asset.objects
            .filter(pk=asset.pk, version=data["version"])
            .exclude(status__in=LOCKED_STATUSES)
            .update(**{f: data[f] for f in COMMON_FIELDS}, version=F("version") + 1)
        )
        if not updated:
            current = Asset.objects.get(pk=asset.pk)
            if current.status in LOCKED_STATUSES:
                raise AssetEditError(
                    f"This asset is {current.get_status_display()} and cannot be edited right now."
                )
            raise AssetEditError(
                "Someone else saved this asset while you were editing it. "
                "Your changes were not saved; please check the latest values and try again."
            )
        if extra:
            model.objects.filter(pk=asset.pk).update(**{f: data[f] for f in extra})

        asset = Asset.objects.get(pk=asset.pk)
        after = snapshot(asset)
        changed = [key for key in after if after[key] != before[key]]
        AuditService.log(
            user, "edit_asset", asset, record_type="Asset",
            before={k: before[k] for k in changed}, after={k: after[k] for k in changed},
        )
        return asset
