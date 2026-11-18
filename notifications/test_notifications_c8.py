"""C8 Notifications: notify() puts messages in the right inbox, and nobody sees another user's inbox."""

from django.test import TestCase
from django.urls import reverse

from assets.models import ITAsset
from circular_campus.test_utils import make_asset, make_request, make_user
from notifications.models import Notification
from notifications.services import link_of, notify, notify_many, record_label, unread_count

PASSWORD = "Test-pass-123"


class NotifyTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_notify_creates_unread_message_linked_to_record(self):
        request = make_request(requester=self.user)
        note = notify(self.user, "Your request was approved.", record=request)
        self.assertEqual(note.linked_record, f"ResourceRequest:{request.pk}")
        self.assertIsNone(note.read_at)
        self.assertEqual(unread_count(self.user), 1)

    def test_asset_subtype_is_linked_as_asset(self):
        laptop = make_asset(model=ITAsset, serial_number="SN-C8-1")
        self.assertEqual(record_label(laptop), f"Asset:{laptop.pk}")

    def test_inactive_user_gets_nothing(self):
        self.user.is_active = False
        self.user.save()
        self.assertIsNone(notify(self.user, "hello"))
        self.assertFalse(Notification.objects.exists())

    def test_notify_many_sends_each_user_once(self):
        other = make_user()
        sent = notify_many([self.user, other, self.user], "New request")
        self.assertEqual(len(sent), 2)

    def test_link_to_asset_page(self):
        asset = make_asset()
        note = notify(self.user, "About your asset", record=asset)
        self.assertEqual(link_of(note), reverse("assets:detail", args=[asset.pk]))

    def test_record_without_page_has_no_link(self):
        note = notify(self.user, "General message")
        self.assertIsNone(link_of(note))


class InboxPageTests(TestCase):
    def setUp(self):
        self.user, self.other = make_user(), make_user()
        self.client.login(email=self.user.email, password=PASSWORD)

    def test_inbox_needs_sign_in(self):
        self.client.logout()
        response = self.client.get(reverse("notifications:inbox"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('notifications:inbox')}")

    def test_inbox_shows_only_own_messages(self):
        notify(self.user, "Mine: request approved")
        notify(self.other, "Theirs: request rejected")
        response = self.client.get(reverse("notifications:inbox"))
        self.assertContains(response, "Mine: request approved")
        self.assertNotContains(response, "Theirs: request rejected")

    def test_menu_shows_unread_count(self):
        notify(self.user, "one")
        notify(self.user, "two")
        response = self.client.get(reverse("home"))
        self.assertContains(response, f'href="{reverse("notifications:inbox")}"')
        self.assertContains(response, '<span class="tag ai">2</span>')

    def test_open_marks_read_and_goes_to_record(self):
        asset = make_asset()
        note = notify(self.user, "About an asset", record=asset)
        response = self.client.post(reverse("notifications:open", args=[note.pk]))
        self.assertRedirects(response, reverse("assets:detail", args=[asset.pk]), fetch_redirect_response=False)
        note.refresh_from_db()
        self.assertIsNotNone(note.read_at)

    def test_cannot_open_another_users_message(self):
        theirs = notify(self.other, "secret")
        self.assertEqual(self.client.post(reverse("notifications:open", args=[theirs.pk])).status_code, 404)
        theirs.refresh_from_db()
        self.assertIsNone(theirs.read_at)

    def test_open_needs_post(self):
        note = notify(self.user, "hello")
        self.assertEqual(self.client.get(reverse("notifications:open", args=[note.pk])).status_code, 405)

    def test_mark_all_read_only_touches_own_messages(self):
        notify(self.user, "a")
        notify(self.user, "b")
        theirs = notify(self.other, "c")
        self.client.post(reverse("notifications:read_all"))
        self.assertEqual(unread_count(self.user), 0)
        theirs.refresh_from_db()
        self.assertIsNone(theirs.read_at)

    def test_unread_filter(self):
        read = notify(self.user, "already read")
        self.client.post(reverse("notifications:open", args=[read.pk]))
        notify(self.user, "still new")
        response = self.client.get(reverse("notifications:inbox"), {"show": "unread"})
        self.assertContains(response, "still new")
        self.assertNotContains(response, "already read")
