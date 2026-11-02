"""C2 Departments and assets: register, view and edit assets of your own department."""

from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from accounts.models import AuditLog, Role, UserRole
from assets.models import Asset, FurnitureAsset, ITAsset
from circular_campus.test_utils import make_asset, make_category, make_department, make_user

PASSWORD = "Test-pass-123"


def with_role(user, name):
    UserRole.objects.create(user=user, role=Role.objects.get_or_create(name=name)[0])
    return user


def form_data(**overrides):
    """A valid Register form for an IT asset; override any field."""
    data = {
        "name": "Synthetic laptop", "kind": "it", "status": "Available", "condition": "Good",
        "category": "", "serial_number": "SN-TEST-001", "tags_text": "laptop, 16GB",
        "description": "", "campus": "Main", "building": "B1", "room": "101",
        "purchase_date": "2024-01-15", "estimated_value_aed": "3500.00", "mass_kg": "1.8",
        "calibration_due": "", "material": "",
    }
    data.update(overrides)
    return data


class AssetPagesTests(TestCase):
    def setUp(self):
        self.dept, self.other_dept = make_department(), make_department()
        self.category = make_category()
        self.custodian = with_role(make_user(department=self.dept), "Custodian")
        self.requester = with_role(make_user(department=self.dept), "Requester")
        self.client.login(email=self.custodian.email, password=PASSWORD)

    def register(self, **overrides):
        return self.client.post(reverse("assets:create"), form_data(category=self.category.pk, **overrides))

    # ---------------------------------------------------------------- access

    def test_pages_need_sign_in(self):
        self.client.logout()
        response = self.client.get(reverse("assets:list"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('assets:list')}")

    def test_requester_cannot_open_asset_pages(self):
        self.client.login(email=self.requester.email, password=PASSWORD)
        self.assertEqual(self.client.get(reverse("assets:list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("assets:create")).status_code, 403)

    def test_list_shows_only_own_department(self):
        mine = make_asset(owner_department=self.dept, name="Our projector")
        make_asset(owner_department=self.other_dept, name="Their microscope")
        response = self.client.get(reverse("assets:list"))
        self.assertContains(response, "Our projector")
        self.assertNotContains(response, "Their microscope")
        self.assertContains(response, reverse("assets:detail", args=[mine.pk]))

    def test_other_department_asset_gives_403_even_by_typing_its_id(self):
        theirs = make_asset(owner_department=self.other_dept)
        self.assertEqual(self.client.get(reverse("assets:detail", args=[theirs.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("assets:edit", args=[theirs.pk])).status_code, 403)
        response = self.client.post(reverse("assets:edit", args=[theirs.pk]), form_data(category=self.category.pk))
        self.assertEqual(response.status_code, 403)

    def test_assets_menu_link_only_for_custodian(self):
        self.assertContains(self.client.get(reverse("home")), f'href="{reverse("assets:list")}"')
        self.client.login(email=self.requester.email, password=PASSWORD)
        self.assertNotContains(self.client.get(reverse("home")), f'href="{reverse("assets:list")}"')

    def test_list_search_and_status_filter(self):
        make_asset(owner_department=self.dept, name="Blue chair", status="Draft")
        make_asset(owner_department=self.dept, name="Red chair", status="Available")
        response = self.client.get(reverse("assets:list"), {"q": "chair", "status": "Available"})
        self.assertContains(response, "Red chair")
        self.assertNotContains(response, "Blue chair")

    # ---------------------------------------------------------------- UC-04 register

    def test_register_it_asset(self):
        response = self.register()
        asset = Asset.objects.get(name="Synthetic laptop")
        self.assertRedirects(response, reverse("assets:detail", args=[asset.pk]))
        self.assertEqual(asset.owner_department, self.dept)  # always the custodian's department
        self.assertEqual(asset.status, "Available")
        self.assertEqual(asset.tags, ["laptop", "16GB"])
        self.assertEqual(ITAsset.objects.get(pk=asset.pk).serial_number, "SN-TEST-001")
        entry = AuditLog.objects.get(action="register_asset")
        self.assertEqual((entry.user, entry.record_type, entry.record_id), (self.custodian, "Asset", asset.pk))
        self.assertEqual(entry.after_value["serial_number"], "SN-TEST-001")

    def test_register_furniture_needs_material(self):
        response = self.register(kind="furniture", serial_number="", material="")
        self.assertContains(response, "Furniture needs a material")
        self.register(kind="furniture", serial_number="", material="Oak")
        self.assertEqual(FurnitureAsset.objects.get().material, "Oak")

    def test_department_cannot_be_chosen_in_the_form(self):
        self.register(owner_department=self.other_dept.pk)
        self.assertEqual(Asset.objects.get().owner_department, self.dept)

    def test_register_rejects_bad_input(self):
        cases = {
            "missing name": ({"name": " "}, "Enter the asset name"),
            "missing serial": ({"serial_number": ""}, "IT equipment needs a serial number"),
            "negative value": ({"estimated_value_aed": "-5"}, "greater than or equal to 0"),
            "zero mass": ({"mass_kg": "0"}, "greater than or equal to 0.001"),
            "future purchase": ({"purchase_date": str(date.today() + timedelta(days=3))}, "cannot be in the future"),
            "bad status": ({"status": "Reserved"}, "Select a valid choice"),
        }
        for label, (overrides, message) in cases.items():
            with self.subTest(label):
                response = self.register(**overrides)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, message)
        self.assertFalse(Asset.objects.exists())

    def test_duplicate_serial_number_is_refused(self):
        self.register()
        response = self.register(name="Second laptop")
        self.assertContains(response, "Another asset already has this serial number")
        self.assertEqual(Asset.objects.count(), 1)

    # ---------------------------------------------------------------- UC-05 edit

    def test_edit_saves_changes_and_audits_only_changed_fields(self):
        self.register()
        asset = Asset.objects.get()
        data = form_data(category=self.category.pk, name="Synthetic laptop (renamed)", condition="Fair",
                         version=asset.version)
        response = self.client.post(reverse("assets:edit", args=[asset.pk]), data)
        self.assertRedirects(response, reverse("assets:detail", args=[asset.pk]))
        asset.refresh_from_db()
        self.assertEqual((asset.name, asset.condition, asset.version), ("Synthetic laptop (renamed)", "Fair", 2))
        entry = AuditLog.objects.get(action="edit_asset")
        self.assertEqual(entry.before_value, {"name": "Synthetic laptop", "condition": "Good"})
        self.assertEqual(entry.after_value, {"name": "Synthetic laptop (renamed)", "condition": "Fair"})

    def test_edit_cannot_change_type_or_status(self):
        self.register()
        asset = Asset.objects.get()
        data = form_data(category=self.category.pk, kind="furniture", material="Oak", status="Draft",
                         version=asset.version)
        self.client.post(reverse("assets:edit", args=[asset.pk]), data)
        asset.refresh_from_db()
        self.assertEqual(asset.status, "Available")
        self.assertTrue(ITAsset.objects.filter(pk=asset.pk).exists())
        self.assertFalse(FurnitureAsset.objects.filter(pk=asset.pk).exists())

    def test_edit_refused_when_someone_else_saved_first(self):
        self.register()
        asset = Asset.objects.get()
        old_version = asset.version
        Asset.objects.filter(pk=asset.pk).update(name="Changed by a colleague", version=old_version + 1)
        data = form_data(category=self.category.pk, name="My change", version=old_version)
        response = self.client.post(reverse("assets:edit", args=[asset.pk]), data, follow=True)
        self.assertContains(response, "Someone else saved this asset")
        asset.refresh_from_db()
        self.assertEqual(asset.name, "Changed by a colleague")
        self.assertFalse(AuditLog.objects.filter(action="edit_asset").exists())

    def test_reserved_asset_cannot_be_edited(self):
        asset = make_asset(owner_department=self.dept, category=self.category, status="Reserved")
        response = self.client.get(reverse("assets:edit", args=[asset.pk]), follow=True)
        self.assertContains(response, "cannot be edited right now")
        data = form_data(category=self.category.pk, kind="general", serial_number="", name="Changed",
                         version=asset.version)
        self.client.post(reverse("assets:edit", args=[asset.pk]), data)
        asset.refresh_from_db()
        self.assertNotEqual(asset.name, "Changed")

    def test_detail_page_shows_the_asset(self):
        self.register()
        asset = Asset.objects.get()
        response = self.client.get(reverse("assets:detail", args=[asset.pk]))
        self.assertContains(response, "Synthetic laptop")
        self.assertContains(response, "SN-TEST-001")
        self.assertContains(response, "IT equipment")
