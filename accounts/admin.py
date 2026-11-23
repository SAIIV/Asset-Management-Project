from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import AuditLog, Role, User
from .services import AuditService


class RolesMixin(forms.Form):
    """Roles are kept in the UserRole table (a user may hold several), so the
    admin form edits them with one checkbox per role."""

    user_roles = forms.ModelMultipleChoiceField(queryset=Role.objects.order_by("name"), required=False,
                                           widget=forms.CheckboxSelectMultiple)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["user_roles"].initial = list(self.instance.roles.all())


class AddUserForm(RolesMixin, UserCreationForm):
    class Meta:
        model = User
        fields = ["email", "name", "department"]


class ChangeUserForm(RolesMixin, UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


def _role_names(user):
    return sorted(user.roles.values_list("name", flat=True)) if user.pk else []


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin pages for our email-based User (no username field).

    This is where the Administrator creates accounts (there is no self sign-up)
    and gives each person a department and roles. Role changes are audited.
    """

    form = ChangeUserForm
    add_form = AddUserForm
    ordering = ["email"]
    list_display = ["email", "name", "department", "role_names", "is_active"]
    list_filter = ["is_active", "is_staff", "department", "roles"]
    search_fields = ["email", "name"]
    fieldsets = [
        (None, {"fields": ["email", "password"]}),
        ("Profile", {"fields": ["name", "department"]}),
        ("Roles", {"fields": ["user_roles"]}),
        ("Access", {"fields": ["is_active", "is_staff", "is_superuser"]}),
        ("Dates", {"fields": ["last_login", "date_joined"]}),
    ]
    add_fieldsets = [(None, {"classes": ["wide"],
                             "fields": ["email", "name", "department", "user_roles", "password1", "password2"]})]

    @admin.display(description="Roles")
    def role_names(self, user):
        return ", ".join(role.name for role in user.roles.all()) or "-"

    def save_model(self, request, obj, form, change):
        self._roles_before = _role_names(User.objects.get(pk=obj.pk)) if change else []
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        user = form.instance
        user.roles.set(form.cleaned_data.get("user_roles") or [])
        after = _role_names(user)
        before = getattr(self, "_roles_before", [])
        if before != after:
            AuditService.log(request.user, "assign_roles", user, before={"roles": before}, after={"roles": after},
                             reason="Changed in the admin site")


admin.site.register(Role)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "user", "action", "record_type", "record_id"]
    list_filter = ["record_type", "action"]
