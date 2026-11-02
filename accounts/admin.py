from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import AuditLog, Role, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin pages for our email-based User (no username field)."""

    ordering = ["email"]
    list_display = ["email", "name", "department", "is_active", "is_staff"]
    list_filter = ["is_active", "is_staff", "department"]
    search_fields = ["email", "name"]
    fieldsets = [
        (None, {"fields": ["email", "password"]}),
        ("Profile", {"fields": ["name", "department"]}),
        ("Access", {"fields": ["is_active", "is_staff", "is_superuser"]}),
        ("Dates", {"fields": ["last_login", "date_joined"]}),
    ]
    add_fieldsets = [(None, {"classes": ["wide"], "fields": ["email", "name", "password1", "password2"]})]


admin.site.register(Role)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "user", "action", "record_type", "record_id"]
    list_filter = ["record_type", "action"]
