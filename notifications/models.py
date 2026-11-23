"""Notifications (store D1): in-app inbox messages."""

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """Inbox message. readAt stays empty until the user reads it."""

    id = models.BigAutoField(primary_key=True, db_column="notificationId")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications", db_column="userId"
    )
    message = models.TextField()
    # The record the message is about, written as "<Table>:<id>", e.g. "ResourceRequest:12".
    linked_record = models.CharField(max_length=80, blank=True, db_column="linkedRecord")
    created_at = models.DateTimeField(auto_now_add=True, db_column="createdAt")
    read_at = models.DateTimeField(null=True, blank=True, db_column="readAt")

    class Meta:
        db_table = "Notification"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "read_at"], name="notification_inbox_idx")]

    def __str__(self):
        return self.message[:60]

    #: how a linked record is named on screen ("ResourceRequest:1" -> "Request #1")
    RECORD_LABELS = {"ResourceRequest": "Request", "Transfer": "Transfer", "Asset": "Asset"}

    @property
    def about(self):
        table, _, pk = self.linked_record.partition(":")
        return f"{self.RECORD_LABELS.get(table, table)} #{pk}" if pk else ""

