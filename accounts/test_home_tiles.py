"""Start page: count tiles and quick actions follow the user's roles."""

from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, UserRole
from circular_campus.test_utils import make_asset, make_department, make_user

PASSWORD = "Test-pass-123"


def with_role(user, name):
    UserRole.objects.create(user=user, role=Role.objects.get_or_create(name=name)[0])
    return user


class HomeTileTests(TestCase):
    def setUp(self):
        self.dept, self.other = make_department(), make_department()
        make_asset(owner_department=self.dept)

    def test_custodian_sees_department_assets_and_register_button(self):
        custodian = with_role(make_user(department=self.dept), "Custodian")
        self.client.login(email=custodian.email, password=PASSWORD)
        page = self.client.get(reverse("home"))
        self.assertContains(page, "Assets in my department")
        self.assertContains(page, f'href="{reverse("assets:create")}"')
        self.assertNotContains(page, "My open requests")

    def test_requester_sees_own_requests_not_assets(self):
        requester = with_role(make_user(department=self.other), "Requester")
        self.client.login(email=requester.email, password=PASSWORD)
        page = self.client.get(reverse("home"))
        self.assertContains(page, "My open requests")
        self.assertContains(page, f'href="{reverse("exchange:request_create")}"')
        self.assertNotContains(page, "Assets in my department")


class AccountPageTests(TestCase):
    def setUp(self):
        self.user = with_role(make_user(department=make_department(), name="Old Name"), "Requester")
        self.client.login(email=self.user.email, password=PASSWORD)

    def test_profile_menu_links_to_account(self):
        page = self.client.get(reverse("home"))
        self.assertContains(page, f'href="{reverse("account")}"')
        self.assertContains(page, "Recent activity")

    def test_change_name(self):
        self.client.post(reverse("account"), {"name": "New Name"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, "New Name")

    def test_change_password_keeps_you_signed_in(self):
        self.assertContains(self.client.get(reverse("account")), f'href="{reverse("change_password")}"')
        response = self.client.post(reverse("change_password"), {
            "old_password": PASSWORD,
            "new_password1": "Green-Campus-2026!", "new_password2": "Green-Campus-2026!"})
        self.assertRedirects(response, reverse("account"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Green-Campus-2026!"))
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)

    def test_wrong_old_password_changes_nothing(self):
        self.client.post(reverse("change_password"), {
            "old_password": "wrong",
            "new_password1": "Green-Campus-2026!", "new_password2": "Green-Campus-2026!"})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))
