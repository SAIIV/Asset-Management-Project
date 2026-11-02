"""Tests for Notification."""

from django.test import TestCase

from circular_campus.test_utils import make_user
from notifications.models import Notification


class NotificationTests(TestCase):
    def test_read_at_empty_until_read(self):
        note = Notification.objects.create(user=make_user(), message="Request #1 approved",
                                           linked_record="ResourceRequest:1")
        self.assertIsNone(note.read_at)
        self.assertIsNotNone(note.created_at)
