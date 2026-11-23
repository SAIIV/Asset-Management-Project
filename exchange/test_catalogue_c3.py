"""C3 Publish and search: only Available, published assets are found, and only the owning custodian publishes."""

from django.test import TestCase
from django.urls import reverse

from accounts.models import AuditLog, Role, UserRole
from assets.models import Asset
from circular_campus.choices import AssetStatus as A
from circular_campus.test_utils import make_asset, make_category, make_department, make_user
from exchange.catalogue import CatalogueError, CatalogueService, search

PASSWORD = "Test-pass-123"


def with_role(user, name):
    UserRole.objects.create(user=user, role=Role.objects.get_or_create(name=name)[0])
    return user


#: what a listing needs (UC-06 step 4)
LISTING = {"description": "Working, with charger", "campus": "Main", "building": "B1", "room": "101"}


class SearchTests(TestCase):
    def setUp(self):
        self.it, self.lab = make_department(name="IT Services"), make_department(name="Chemistry")
        self.laptops, self.chairs = make_category(name="Laptops"), make_category(name="Chairs")
        self.laptop = make_asset(name="Dell laptop", category=self.laptops, owner_department=self.it,
                                 condition="Good", status=A.AVAILABLE, is_listed=True, tags=["16gb"])
        self.chair = make_asset(name="Office chair", category=self.chairs, owner_department=self.lab,
                                condition="Fair", status=A.AVAILABLE, is_listed=True)

    def test_only_listed_and_available_are_found(self):
        make_asset(name="Hidden laptop", status=A.AVAILABLE, is_listed=False)
        make_asset(name="Reserved laptop", status=A.RESERVED, is_listed=True)
        make_asset(name="Draft laptop", status=A.DRAFT, is_listed=True)
        self.assertEqual(list(search("laptop")), [self.laptop])

    def test_keyword_matches_name_description_category_and_tag(self):
        self.assertIn(self.laptop, search("dell"))
        self.assertIn(self.laptop, search("Laptops"))
        self.assertIn(self.laptop, search("16gb"))
        self.assertEqual(list(search("dell chair")), [])  # every word must match

    def test_filters(self):
        self.assertEqual(list(search(category=self.chairs.pk)), [self.chair])
        self.assertEqual(list(search(condition="Good")), [self.laptop])
        self.assertEqual(list(search(department=self.lab.pk)), [self.chair])


class PublishTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_publish_available_asset_writes_audit_row(self):
        asset = make_asset(status=A.AVAILABLE, **LISTING)
        CatalogueService.publish(self.user, asset)
        self.assertTrue(Asset.objects.get(pk=asset.pk).is_listed)
        self.assertTrue(AuditLog.objects.filter(action="publish_asset", record_id=asset.pk).exists())

    def test_cannot_publish_reserved_or_under_maintenance(self):
        for status in (A.RESERVED, A.UNDER_MAINTENANCE, A.IN_USE):
            asset = make_asset(status=status, **LISTING)
            with self.assertRaises(CatalogueError):
                CatalogueService.publish(self.user, asset)
            self.assertFalse(Asset.objects.get(pk=asset.pk).is_listed)

    def test_missing_listing_fields_block_publishing(self):
        asset = make_asset(status=A.AVAILABLE, description="Working", campus="Main")
        with self.assertRaisesMessage(CatalogueError, "fill in the building, room"):
            CatalogueService.publish(self.user, asset)
        self.assertFalse(Asset.objects.get(pk=asset.pk).is_listed)

    def test_unserviceable_asset_is_not_published(self):
        broken = make_asset(status=A.AVAILABLE, condition="NeedsRepair", **LISTING)
        with self.assertRaisesMessage(CatalogueError, "needs repair"):
            CatalogueService.publish(self.user, broken)
        failed = make_asset(status=A.AVAILABLE, serviceability=False, **LISTING)
        with self.assertRaisesMessage(CatalogueError, "not serviceable"):
            CatalogueService.publish(self.user, failed)

    def test_draft_is_made_available_and_listed(self):
        asset = make_asset(status=A.DRAFT, **LISTING)
        CatalogueService.publish(self.user, asset)
        asset.refresh_from_db()
        self.assertEqual((asset.status, asset.is_listed), (A.AVAILABLE, True))
        self.assertTrue(AuditLog.objects.filter(action="change_asset_status", record_id=asset.pk).exists())

    def test_unpublish(self):
        asset = make_asset(status=A.AVAILABLE, is_listed=True)
        CatalogueService.unpublish(self.user, asset, reason="needed again")
        self.assertFalse(Asset.objects.get(pk=asset.pk).is_listed)
        self.assertEqual(AuditLog.objects.get(action="unpublish_asset").reason, "needed again")


class CataloguePageTests(TestCase):
    def setUp(self):
        self.dept, self.other = make_department(), make_department()
        self.custodian = with_role(make_user(department=self.dept), "Custodian")
        self.requester = with_role(make_user(department=self.other), "Requester")
        self.listed = make_asset(name="Listed projector", owner_department=self.dept,
                                 status=A.AVAILABLE, is_listed=True)

    def login(self, user):
        self.client.login(email=user.email, password=PASSWORD)

    def test_requester_searches_and_opens_listed_item(self):
        self.login(self.requester)
        response = self.client.get(reverse("exchange:catalogue"), {"q": "projector"})
        self.assertContains(response, "Listed projector")
        detail = self.client.get(reverse("exchange:catalogue_detail", args=[self.listed.pk]))
        self.assertContains(detail, "Listed projector")

    def test_unlisted_item_is_404_even_by_typing_its_id(self):
        hidden = make_asset(owner_department=self.dept, status=A.AVAILABLE, is_listed=False)
        self.login(self.requester)
        self.assertEqual(self.client.get(reverse("exchange:catalogue_detail", args=[hidden.pk])).status_code, 404)

    def test_catalogue_needs_sign_in_and_role(self):
        response = self.client.get(reverse("exchange:catalogue"))
        self.assertEqual(response.status_code, 302)
        self.login(make_user())  # no role
        self.assertEqual(self.client.get(reverse("exchange:catalogue")).status_code, 403)

    def test_menu_link_for_requester(self):
        self.login(self.requester)
        self.assertContains(self.client.get(reverse("home")), f'href="{reverse("exchange:catalogue")}"')

    def test_custodian_publishes_from_asset_page(self):
        asset = make_asset(owner_department=self.dept, status=A.AVAILABLE, **LISTING)
        self.login(self.custodian)
        self.assertContains(self.client.get(reverse("assets:detail", args=[asset.pk])), "Publish to catalogue")
        self.client.post(reverse("exchange:publish", args=[asset.pk]))
        self.assertTrue(Asset.objects.get(pk=asset.pk).is_listed)

    def test_refusal_is_shown_on_the_asset_page(self):
        asset = make_asset(owner_department=self.dept, status=A.AVAILABLE)
        self.login(self.custodian)
        response = self.client.post(reverse("exchange:publish", args=[asset.pk]), follow=True)
        self.assertContains(response, "Not published yet: fill in the description, campus, building, room")
        self.assertFalse(Asset.objects.get(pk=asset.pk).is_listed)

    def test_requester_cannot_publish(self):

        asset = make_asset(owner_department=self.other, status=A.AVAILABLE)
        self.login(self.requester)
        self.assertEqual(self.client.post(reverse("exchange:publish", args=[asset.pk])).status_code, 403)
        self.assertFalse(Asset.objects.get(pk=asset.pk).is_listed)

    def test_custodian_cannot_publish_other_departments_asset(self):
        theirs = make_asset(owner_department=self.other, status=A.AVAILABLE)
        self.login(self.custodian)
        self.assertEqual(self.client.post(reverse("exchange:publish", args=[theirs.pk])).status_code, 403)

    def test_publish_needs_post(self):
        self.login(self.custodian)
        self.assertEqual(self.client.get(reverse("exchange:publish", args=[self.listed.pk])).status_code, 405)

    def test_custodian_unpublishes(self):
        self.login(self.custodian)
        self.client.post(reverse("exchange:unpublish", args=[self.listed.pk]))
        self.assertFalse(Asset.objects.get(pk=self.listed.pk).is_listed)
