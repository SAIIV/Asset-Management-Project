from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "message", "linked_record", "created_at", "read_at"]
    list_filter = ["read_at"]
    search_fields = ["message", "user__email"]
