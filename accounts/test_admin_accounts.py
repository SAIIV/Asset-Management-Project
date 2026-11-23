"""The Administrator creates accounts and gives roles in the admin site (no self sign-up)."""

from django.test import TestCase
from django.urls import reverse

from accounts.models import AuditLog, Role, User
from circular_campus.test_utils import make_user


def with_role(user, name):
    user.roles.add(Role.objects.get_or_create(name=name)[0])
    return user


class AdminCreatesAccounts(TestCase):
    def setUp(self):
        for name in ("Requester", "Custodian", "Approver"):
            Role.objects.get_or_create(name=name)
        self.admin = make_user(email="boss@example.com")
        User.objects.filter(pk=self.admin.pk).update(is_staff=True, is_superuser=True)
        self.client.force_login(User.objects.get(pk=self.admin.pk))

    def test_new_account_gets_its_roles(self):
        requester = Role.objects.get(name="Requester")
        custodian = Role.objects.get(name="Custodian")
        response = self.client.post(reverse("admin:accounts_user_add"), {
            "email": "new.person@example.com", "name": "New Person", "department": "",
            "user_roles": [requester.pk, custodian.pk],
            "password1": "Long-enough-pass-2026", "password2": "Long-enough-pass-2026",
        })
        self.assertEqual(response.status_code, 302, getattr(response, "context", None) and response.context["adminform"].form.errors)
        user = User.objects.get(email="new.person@example.com")
        self.assertEqual(sorted(user.roles.values_list("name", flat=True)), ["Custodian", "Requester"])
        self.assertTrue(user.check_password("Long-enough-pass-2026"))
        self.assertTrue(AuditLog.objects.filter(action="assign_roles", record_id=user.pk).exists())

    def test_changing_roles_is_audited(self):
        person = with_role(make_user(email="p@example.com"), "Requester")
        page = self.client.get(reverse("admin:accounts_user_change", args=[person.pk]))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'name="user_roles"')
        approver = Role.objects.get(name="Approver")
        form = page.context["adminform"].form
        data = {name: field.value() for name, field in ((n, form[n]) for n in form.fields) if field.value() is not None}
        data.update({"user_roles": [approver.pk], "date_joined_0": "2026-11-23", "date_joined_1": "10:00:00",
                     "last_login_0": "", "last_login_1": ""})
        data["is_active"] = "on"
        data.pop("is_staff", None)
        data.pop("is_superuser", None)
        data.pop("password", None)
        response = self.client.post(reverse("admin:accounts_user_change", args=[person.pk]), data)
        self.assertEqual(response.status_code, 302, response.context and response.context["adminform"].form.errors)
        self.assertEqual(list(person.roles.values_list("name", flat=True)), ["Approver"])
        row = AuditLog.objects.get(action="assign_roles", record_id=person.pk)
        self.assertEqual(row.before_value, {"roles": ["Requester"]})
        self.assertEqual(row.after_value, {"roles": ["Approver"]})
