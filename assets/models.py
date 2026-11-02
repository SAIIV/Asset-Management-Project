"""Assets & Catalogue (stores D2, D5, D6) and Maintenance & Lifecycle records.

Tables: Department, Category, Asset, ITAsset, LabEquipment, FurnitureAsset,
AssetCollection, AssetCollectionItem, Attachment, Inspection,
MaintenanceRecord, LifecycleAction (Design Document Section 9).
"""

from datetime import date

from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from pgvector.django import HnswIndex, VectorField

from circular_campus.choices import (
    AssetStatus,
    Condition,
    FileKind,
    LifecycleActionType,
    LifecycleStatus,
    MaintenanceStatus,
    choices_check,
)

#: all-MiniLM-L6-v2 produces 384 numbers per text (AD-3)
EMBEDDING_DIMENSIONS = 384


class Department(models.Model):
    """Owning and receiving departments. Name unique."""

    id = models.BigAutoField(primary_key=True, db_column="departmentId")
    name = models.CharField(max_length=120, unique=True)
    building = models.CharField(max_length=120, blank=True)

    class Meta:
        db_table = "Department"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Category(models.Model):
    """Category tree used by classification. A top category has no parent; no cycles."""

    id = models.BigAutoField(primary_key=True, db_column="categoryId")
    parent_category = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="children",
        db_column="parentCategoryId",
    )
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    embedding = VectorField(dimensions=EMBEDDING_DIMENSIONS, null=True, blank=True)

    class Meta:
        db_table = "Category"
        verbose_name_plural = "categories"
        ordering = ["name"]
        constraints = [
            # A category can never be its own parent (the simplest cycle).
            models.CheckConstraint(
                condition=Q(parent_category__isnull=True) | ~Q(parent_category=models.F("id")),
                name="category_not_own_parent",
            ),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        # Longer cycles (A -> B -> A) are checked here, by walking up the tree.
        node, seen = self.parent_category, {self.pk}
        while node is not None:
            if node.pk in seen:
                raise ValidationError("A category cannot be placed under one of its own sub-categories.")
            seen.add(node.pk)
            node = node.parent_category


class Asset(models.Model):
    """One physical item (data dictionary: Asset).

    status is one of the Figure 56 states; condition is New, Good, Fair or
    NeedsRepair; massKg and estimatedValueAED may be empty but are never 0 by
    default; the asset's age is computed from purchaseDate, not stored.
    """

    id = models.BigAutoField(primary_key=True, db_column="assetId")
    owner_department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="assets", db_column="ownerDepartmentId"
    )
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="assets", db_column="categoryId")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    condition = models.CharField(max_length=20, choices=Condition.choices)
    status = models.CharField(max_length=20, choices=AssetStatus.choices, default=AssetStatus.DRAFT)
    # Empty until the asset is inspected; then true (serviceable) or false.
    serviceability = models.BooleanField(null=True, blank=True)
    campus = models.CharField(max_length=80, blank=True)
    building = models.CharField(max_length=80, blank=True)
    room = models.CharField(max_length=40, blank=True)
    purchase_date = models.DateField(null=True, blank=True, db_column="purchaseDate")
    estimated_value_aed = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, db_column="estimatedValueAED"
    )
    mass_kg = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, db_column="massKg")
    tags = ArrayField(models.CharField(max_length=40), default=list, blank=True)
    is_listed = models.BooleanField(default=False, db_column="isListed")
    embedding = VectorField(dimensions=EMBEDDING_DIMENSIONS, null=True, blank=True)
    version = models.PositiveIntegerField(default=1)  # optimistic locking

    class Meta:
        db_table = "Asset"
        ordering = ["id"]
        constraints = [
            choices_check("condition", Condition, "asset_condition_valid"),
            choices_check("status", AssetStatus, "asset_status_valid"),
            models.CheckConstraint(
                condition=Q(mass_kg__isnull=True) | Q(mass_kg__gt=0), name="asset_mass_positive_or_empty"
            ),
            models.CheckConstraint(
                condition=Q(estimated_value_aed__isnull=True) | Q(estimated_value_aed__gte=0),
                name="asset_value_not_negative",
            ),
            models.CheckConstraint(condition=Q(version__gte=1), name="asset_version_positive"),
        ]
        indexes = [
            models.Index(fields=["status", "is_listed"], name="asset_status_listed_idx"),
            models.Index(fields=["condition"], name="asset_condition_idx"),
            # Fast "most similar asset" search with pgvector (AI #2 matching).
            HnswIndex(
                name="asset_embedding_hnsw_idx",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def __str__(self):
        return f"#{self.pk} {self.name}"

    @property
    def asset_age_years(self):
        """/assetAge in the ER diagram: derived from purchaseDate, never stored."""
        if not self.purchase_date:
            return None
        return round((date.today() - self.purchase_date).days / 365.25, 1)


class ITAsset(Asset):
    """IT equipment details. Shares the assetId key with Asset (one row at most per asset)."""

    asset = models.OneToOneField(
        Asset, on_delete=models.CASCADE, parent_link=True, primary_key=True, db_column="assetId",
        related_name="it_details",
    )
    serial_number = models.CharField(max_length=100, unique=True, db_column="serialNumber")

    class Meta:
        db_table = "ITAsset"
        verbose_name = "IT asset"


class LabEquipment(Asset):
    """Laboratory equipment details. calibrationDue may be empty."""

    asset = models.OneToOneField(
        Asset, on_delete=models.CASCADE, parent_link=True, primary_key=True, db_column="assetId",
        related_name="lab_details",
    )
    calibration_due = models.DateField(null=True, blank=True, db_column="calibrationDue")

    class Meta:
        db_table = "LabEquipment"
        verbose_name = "lab equipment"
        verbose_name_plural = "lab equipment"


class FurnitureAsset(Asset):
    """Furniture details. material is required."""

    asset = models.OneToOneField(
        Asset, on_delete=models.CASCADE, parent_link=True, primary_key=True, db_column="assetId",
        related_name="furniture_details",
    )
    material = models.CharField(max_length=80)

    class Meta:
        db_table = "FurnitureAsset"
        constraints = [models.CheckConstraint(condition=~Q(material=""), name="furniture_material_required")]


class AssetCollection(models.Model):
    """A named set of assets, e.g. for an event. Deleting a collection keeps its assets."""

    id = models.BigAutoField(primary_key=True, db_column="collectionId")
    title = models.CharField(max_length=200)
    assets = models.ManyToManyField(Asset, through="AssetCollectionItem", related_name="collections", blank=True)

    class Meta:
        db_table = "AssetCollection"
        ordering = ["title"]
        constraints = [models.CheckConstraint(condition=~Q(title=""), name="collection_title_required")]

    def __str__(self):
        return self.title


class AssetCollectionItem(models.Model):
    """One asset in one collection. (collectionId, assetId) unique; deleted with its collection."""

    id = models.BigAutoField(primary_key=True, db_column="itemId")
    collection = models.ForeignKey(AssetCollection, on_delete=models.CASCADE, db_column="collectionId")
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, db_column="assetId")

    class Meta:
        db_table = "AssetCollectionItem"
        constraints = [
            models.UniqueConstraint(fields=["collection", "asset"], name="collection_item_unique"),
        ]


class Attachment(models.Model):
    """Photo or specification PDF of an asset (weak entity, key (assetId, attachmentNo)).

    At most one photo and one PDF per asset; sha256 detects a changed file;
    deleted with its asset.
    """

    pk = models.CompositePrimaryKey("asset", "attachment_no")
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="attachments", db_column="assetId")
    attachment_no = models.PositiveSmallIntegerField(db_column="attachmentNo")
    kind = models.CharField(max_length=10, choices=FileKind.choices)
    file_path = models.CharField(max_length=500, db_column="filePath")
    size_bytes = models.PositiveIntegerField(db_column="sizeBytes")
    sha256 = models.CharField(max_length=64)

    class Meta:
        db_table = "Attachment"
        constraints = [
            choices_check("kind", FileKind, "attachment_kind_valid"),
            models.UniqueConstraint(fields=["asset", "kind"], name="attachment_one_per_kind"),
            models.CheckConstraint(condition=Q(sha256__regex=r"^[0-9a-f]{64}$"), name="attachment_sha256_format"),
        ]


class Inspection(models.Model):
    """Recorded condition check. serviceable is true or false, never empty."""

    id = models.BigAutoField(primary_key=True, db_column="inspectionId")
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="inspections", db_column="assetId")
    finding = models.TextField()
    serviceable = models.BooleanField()  # NOT NULL in the database
    inspected_at = models.DateTimeField(db_column="inspectedAt")

    class Meta:
        db_table = "Inspection"
        ordering = ["-inspected_at"]


class MaintenanceRecord(models.Model):
    """Fault, repair and its cost. cost (AED) >= 0; completedAt set only in Completed."""

    id = models.BigAutoField(primary_key=True, db_column="maintenanceId")
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="maintenance_records", db_column="assetId")
    inspection = models.ForeignKey(
        Inspection, on_delete=models.SET_NULL, null=True, blank=True, related_name="maintenance_records",
        db_column="inspectionId",
    )
    reported_at = models.DateTimeField(db_column="reportedAt")
    action = models.TextField()
    cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=MaintenanceStatus.choices, default=MaintenanceStatus.REPORTED)
    completed_at = models.DateTimeField(null=True, blank=True, db_column="completedAt")

    class Meta:
        db_table = "MaintenanceRecord"
        ordering = ["-reported_at"]
        constraints = [
            choices_check("status", MaintenanceStatus, "maintenance_status_valid"),
            models.CheckConstraint(condition=Q(cost__isnull=True) | Q(cost__gte=0), name="maintenance_cost_not_negative"),
            models.CheckConstraint(
                condition=(Q(status=MaintenanceStatus.COMPLETED, completed_at__isnull=False)
                           | (~Q(status=MaintenanceStatus.COMPLETED) & Q(completed_at__isnull=True))),
                name="maintenance_completed_at_only_when_completed",
            ),
        ]


class LifecycleAction(models.Model):
    """Proposed donation, recycling or disposal. executionEvidence required before Executed."""

    id = models.BigAutoField(primary_key=True, db_column="actionId")
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="lifecycle_actions", db_column="assetId")
    action = models.CharField(max_length=20, choices=LifecycleActionType.choices)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.PROPOSED)
    execution_evidence = models.TextField(blank=True, db_column="executionEvidence")

    class Meta:
        db_table = "LifecycleAction"
        constraints = [
            choices_check("action", LifecycleActionType, "lifecycle_action_valid"),
            choices_check("status", LifecycleStatus, "lifecycle_status_valid"),
            models.CheckConstraint(
                condition=~Q(status=LifecycleStatus.EXECUTED) | ~Q(execution_evidence=""),
                name="lifecycle_executed_needs_evidence",
            ),
        ]

    def __str__(self):
        return f"{self.action} of asset #{self.asset_id} ({self.status})"
