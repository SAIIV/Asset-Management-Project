"""Tests for the asset tables and the seed_data command."""

from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase

from assets.models import (
    Asset, AssetCollection, AssetCollectionItem, Attachment, Category, FurnitureAsset, ITAsset,
    LifecycleAction, MaintenanceRecord,
)
from circular_campus.test_utils import make_asset, make_category, now


class AssetConstraintTests(TestCase):
    def test_subclass_shares_asset_id_and_is_deleted_with_asset(self):
        laptop = make_asset(ITAsset, serial_number="SN-1")
        self.assertEqual(Asset.objects.get(pk=laptop.pk).it_details.serial_number, "SN-1")
        Asset.objects.get(pk=laptop.pk).delete()
        self.assertFalse(ITAsset.objects.exists())

    def test_serial_number_is_unique(self):
        make_asset(ITAsset, serial_number="SN-1")
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_asset(ITAsset, serial_number="SN-1")

    def test_condition_and_status_only_accept_enum_values(self):
        asset = make_asset()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Asset.objects.filter(pk=asset.pk).update(condition="Broken")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Asset.objects.filter(pk=asset.pk).update(status="Lost")

    def test_new_asset_starts_as_draft_with_empty_value_and_mass(self):
        asset = make_asset()
        self.assertEqual(asset.status, "Draft")
        self.assertIsNone(asset.mass_kg)
        self.assertIsNone(asset.estimated_value_aed)

    def test_mass_cannot_be_zero(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_asset(mass_kg=0)

    def test_furniture_material_is_required(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_asset(FurnitureAsset, material="")

    def test_one_photo_and_one_pdf_per_asset(self):
        asset = make_asset()
        Attachment.objects.create(asset=asset, attachment_no=1, kind="photo", file_path="a.jpg",
                                  size_bytes=10, sha256="a" * 64)
        Attachment.objects.create(asset=asset, attachment_no=2, kind="pdf", file_path="a.pdf",
                                  size_bytes=10, sha256="b" * 64)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Attachment.objects.create(asset=asset, attachment_no=3, kind="photo", file_path="b.jpg",
                                      size_bytes=10, sha256="c" * 64)

    def test_collection_item_unique_and_collection_delete_keeps_assets(self):
        asset = make_asset()
        collection = AssetCollection.objects.create(title="Open day")
        AssetCollectionItem.objects.create(collection=collection, asset=asset)
        with self.assertRaises(IntegrityError), transaction.atomic():
            AssetCollectionItem.objects.create(collection=collection, asset=asset)
        collection.delete()
        self.assertTrue(Asset.objects.filter(pk=asset.pk).exists())
        self.assertFalse(AssetCollectionItem.objects.exists())

    def test_collection_title_required(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            AssetCollection.objects.create(title="")


class CategoryTests(TestCase):
    def test_category_cannot_be_its_own_parent(self):
        category = make_category()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Category.objects.filter(pk=category.pk).update(parent_category=category)

    def test_longer_cycles_are_rejected_by_clean(self):
        top = make_category()
        child = make_category(parent_category=top)
        top.parent_category = child
        with self.assertRaises(ValidationError):
            top.clean()


class MaintenanceAndLifecycleTests(TestCase):
    def test_cost_not_negative(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            MaintenanceRecord.objects.create(asset=make_asset(), reported_at=now(), action="fix", cost=-1)

    def test_completed_at_only_in_completed(self):
        asset = make_asset()
        with self.assertRaises(IntegrityError), transaction.atomic():
            MaintenanceRecord.objects.create(asset=asset, reported_at=now(), action="fix", completed_at=now())
        with self.assertRaises(IntegrityError), transaction.atomic():
            MaintenanceRecord.objects.create(asset=asset, reported_at=now(), action="fix", status="Completed")
        MaintenanceRecord.objects.create(asset=asset, reported_at=now(), action="fix", status="Completed",
                                         completed_at=now())

    def test_executed_needs_evidence(self):
        asset = make_asset()
        with self.assertRaises(IntegrityError), transaction.atomic():
            LifecycleAction.objects.create(asset=asset, action="Recycling", reason="old", status="Executed")
        LifecycleAction.objects.create(asset=asset, action="Recycling", reason="old", status="Executed",
                                       execution_evidence="Recycler receipt R-1 (synthetic)")


class SeedDataTests(TestCase):
    def test_seed_creates_synthetic_data_and_can_run_twice(self):
        from accounts.models import User
        from assets.models import Department

        call_command("seed_data", stdout=StringIO())
        call_command("seed_data", stdout=StringIO())

        self.assertEqual(Department.objects.count(), 5)
        self.assertTrue(all("Synthetic" in d.name for d in Department.objects.all()))
        self.assertEqual(Asset.objects.count(), 50)
        self.assertEqual(Asset.objects.filter(tags__contains=["synthetic"]).count(), 50)
        self.assertTrue(ITAsset.objects.exists() and FurnitureAsset.objects.exists())
        roles = {u.roles.get().name for u in User.objects.all()}
        self.assertEqual(roles, {"Requester", "Custodian", "Approver", "Administrator"})
