"""Fixes from testing (19 Nov): menu shows only usable links, inbox names records, one date format."""

from datetime import date

from django.template import Context, Template
from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, UserRole
from circular_campus.test_utils import make_department, make_user
from notifications.models import Notification

PASSWORD = "Test-pass-123"


def with_role(user, name):
    UserRole.objects.create(user=user, role=Role.objects.get_or_create(name=name)[0])
    return user


class MenuTests(TestCase):
    def test_requester_sees_only_links_they_can_use(self):
        requester = with_role(make_user(department=make_department()), "Requester")
        self.client.login(email=requester.email, password=PASSWORD)
        page = self.client.get(reverse("home")).content.decode()
        self.assertIn(f'href="{reverse("exchange:catalogue")}"', page)
        self.assertNotIn(f'href="{reverse("assets:list")}"', page)
        self.assertNotIn(">Matches<", page)
        self.assertIn(f'href="{reverse("maintenance:list")}"', page)  # requesters may report a fault (UC-19)
        self.assertNotIn(f'href="{reverse("transfers:approvals")}"', page)
        self.assertNotIn('href="#"', page)

    def test_custodian_requests_link_goes_to_incoming(self):
        custodian = with_role(make_user(department=make_department()), "Custodian")
        self.client.login(email=custodian.email, password=PASSWORD)
        self.assertContains(self.client.get(reverse("home")), f'href="{reverse("transfers:incoming")}"')


class InboxAndDateTests(TestCase):
    def test_inbox_names_the_record(self):
        user = make_user()
        Notification.objects.create(user=user, message="Request submitted", linked_record="ResourceRequest:7")
        self.client.login(email=user.email, password=PASSWORD)
        response = self.client.get(reverse("notifications:inbox"))
        self.assertContains(response, "Request #7")
        self.assertNotContains(response, "ResourceRequest:7")

    def test_one_date_format(self):
        self.assertEqual(Template("{{ d }}").render(Context({"d": date(2026, 11, 20)})), "20 Nov 2026")
