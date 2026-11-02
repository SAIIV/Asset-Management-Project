"""C1 Login and roles: sign-in, sign-out and the can() access matrix."""

from io import StringIO

from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.test import RequestFactory, TestCase
from django.urls import reverse

from accounts.decorators import permission_required
from accounts.models import AuditLog, Role, User, UserRole
from accounts.permissions import Action, can
from circular_campus.test_utils import make_asset, make_department, make_request, make_user
from transfers.models import Approval

PASSWORD = "Synthetic-Demo-2026"
SEEDED = {
    "Requester": "requester@circular-campus.example",
    "Custodian": "custodian@circular-campus.example",
    "Approver": "approver@circular-campus.example",
    "Administrator": "admin@circular-campus.example",
}


def give_role(user, name):
    UserRole.objects.create(user=user, role=Role.objects.get_or_create(name=name)[0])
    user.__dict__.pop("_role_names", None)
    return user


class SignInTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_data", stdout=StringIO())

    def test_each_of_the_four_test_users_can_sign_in(self):
        for role, email in SEEDED.items():
            with self.subTest(role=role):
                response = self.client.post(reverse("login"), {"username": email, "password": PASSWORD}, follow=True)
                self.assertRedirects(response, reverse("home"))
                self.assertContains(response, f'<span class="role">{role}</span>', html=False)
                self.client.post(reverse("logout"))

    def test_wrong_password_gives_generic_message_and_is_audited(self):
        response = self.client.post(reverse("login"), {"username": SEEDED["Requester"], "password": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a correct email and password")
        failed = AuditLog.objects.get(action="sign_in_failed")
        self.assertIsNone(failed.user)
        self.assertNotIn("wrong", str(failed.before_value) + str(failed.after_value) + failed.reason)

    def test_disabled_account_cannot_sign_in(self):
        User.objects.filter(email=SEEDED["Requester"]).update(is_active=False)
        response = self.client.post(reverse("login"), {"username": SEEDED["Requester"], "password": PASSWORD})
        self.assertContains(response, "Please enter a correct email and password")  # same generic message

    def test_sign_in_and_sign_out_are_audited_and_sign_out_ends_session(self):
        self.client.post(reverse("login"), {"username": SEEDED["Approver"], "password": PASSWORD})
        self.assertTrue(AuditLog.objects.filter(action="sign_in", user__email=SEEDED["Approver"]).exists())
        self.client.post(reverse("logout"))
        self.assertTrue(AuditLog.objects.filter(action="sign_out").exists())
        self.assertRedirects(self.client.get(reverse("home")), f"{reverse('login')}?next=/")

    def test_sign_out_needs_post(self):
        self.client.post(reverse("login"), {"username": SEEDED["Approver"], "password": PASSWORD})
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)

    def test_home_needs_sign_in(self):
        self.assertRedirects(self.client.get(reverse("home")), f"{reverse('login')}?next=/")

    def test_start_page_lists_what_the_role_can_do(self):
        self.client.post(reverse("login"), {"username": SEEDED["Custodian"], "password": PASSWORD})
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Register or edit an asset")
        self.assertNotContains(response, "Approve a request")


class AccessMatrixTests(TestCase):
    def setUp(self):
        self.dept, self.other_dept = make_department(), make_department()
        self.requester = give_role(make_user(department=self.dept), "Requester")
        self.custodian = give_role(make_user(department=self.dept), "Custodian")
        self.approver = give_role(make_user(department=self.dept), "Approver")
        self.admin = give_role(make_user(department=self.dept), "Administrator")

    def test_default_is_deny(self):
        nobody = make_user(department=self.dept)
        self.assertFalse(any(can(nobody, action) for action in Action))

    def test_nobody_may_edit_the_audit_log(self):
        for user in (self.requester, self.custodian, self.approver, self.admin):
            self.assertFalse(can(user, Action.EDIT_AUDIT))

    def test_custodian_registers_assets_only_for_own_department(self):
        own = make_asset(owner_department=self.dept)
        other = make_asset(owner_department=self.other_dept)
        self.assertTrue(can(self.custodian, Action.REGISTER_ASSET, own))
        self.assertFalse(can(self.custodian, Action.REGISTER_ASSET, other))
        self.assertFalse(can(self.requester, Action.REGISTER_ASSET, own))

    def test_approver_never_approves_own_request(self):
        own = make_request(requester=self.approver)
        someone_elses = make_request(requester=self.requester)
        self.assertFalse(can(self.approver, Action.APPROVE_REQUEST, own))
        self.assertTrue(can(self.approver, Action.APPROVE_REQUEST, someone_elses))

    def test_user_with_requester_and_approver_roles_still_cannot_self_approve(self):
        both = give_role(give_role(make_user(department=self.dept), "Requester"), "Approver")
        self.assertFalse(can(both, Action.APPROVE_REQUEST, make_request(requester=both)))

    def test_approval_assigned_to_someone_else_is_denied(self):
        other_approver = give_role(make_user(department=self.dept), "Approver")
        approval = Approval.objects.create(approver=other_approver, request=make_request(requester=self.requester))
        self.assertFalse(can(self.approver, Action.APPROVE_REQUEST, approval))
        self.assertTrue(can(other_approver, Action.APPROVE_REQUEST, approval))

    def test_administrator_has_no_business_approval(self):
        self.assertTrue(can(self.admin, Action.MANAGE_USERS))
        self.assertFalse(can(self.admin, Action.APPROVE_REQUEST))
        self.assertFalse(can(self.admin, Action.REGISTER_ASSET))

    def test_only_the_requester_confirms_receipt(self):
        request = make_request(requester=self.requester)
        other_requester = give_role(make_user(department=self.dept), "Requester")
        self.assertTrue(can(self.requester, Action.CONFIRM_RECEIPT, request))
        self.assertFalse(can(other_requester, Action.CONFIRM_RECEIPT, request))

    def test_disabled_user_can_do_nothing(self):
        self.custodian.is_active = False
        self.assertFalse(can(self.custodian, Action.REGISTER_ASSET))

    def test_decorator_denies_with_403(self):
        @permission_required(Action.MANAGE_USERS)
        def view(request):
            return "ok"

        request = RequestFactory().get("/")
        request.user = self.requester
        with self.assertRaises(PermissionDenied):
            view(request)
        request.user = self.admin
        self.assertEqual(view(request), "ok")
