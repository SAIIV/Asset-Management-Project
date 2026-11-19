from django.contrib import admin

from .models import Approval, Reservation, Transfer


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ["id", "request", "asset", "status", "reserved_at", "released_at"]
    list_filter = ["status"]


@admin.register(Approval)
class ApprovalAdmin(admin.ModelAdmin):
    list_display = ["id", "request", "approver", "decision", "decided_at"]
    list_filter = ["decision"]


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ["id", "asset", "request", "status", "released_at", "received_at"]
    list_filter = ["status", "type"]
