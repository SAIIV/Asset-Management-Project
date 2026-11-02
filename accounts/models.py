"""Accounts & Administration (store D1 and D7): User, Role, UserRole, AuditLog.

Table and column names follow the Design Document data dictionary (Section 9.2)
and Figure 63 exactly, using db_table / db_column. In Python code the same
fields use normal Django snake_case names, e.g. Asset.estimated_value_aed is
the column "estimatedValueAED".
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models

from circular_campus.choices import RoleName, choices_check


class UserManager(BaseUserManager):
    """Users sign in with their email address (email is unique)."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("Users must have an email address.")
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)  # stored as a PBKDF2 hash, never plain text
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra)


class User(AbstractUser):
    """A person who signs in (data dictionary: User).

    Rules kept by the database: email unique; only the password hash is stored
    (Django PBKDF2); accounts are deactivated (isActive false), never deleted.
    """

    # Django's username / first / last name are replaced by email + name.
    username = None
    first_name = None
    last_name = None

    id = models.BigAutoField(primary_key=True, db_column="userId")
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True, db_column="email")
    password = models.CharField(max_length=128, db_column="passwordHash")
    is_active = models.BooleanField(default=True, db_column="isActive")
    department = models.ForeignKey(
        "assets.Department",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
        db_column="departmentId",
    )
    roles = models.ManyToManyField("Role", through="UserRole", related_name="users", blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    class Meta:
        db_table = "User"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} <{self.email}>"

    @property
    def initials(self):
        """Two letters for the avatar in the top bar, e.g. "Synthetic Custodian" -> "SC"."""
        return "".join(part[0] for part in self.name.split()[:2]).upper() or self.email[:1].upper()

    def has_role(self, role_name):
        """True if the user holds the role, e.g. user.has_role(RoleName.APPROVER)."""
        return self.roles.filter(name=role_name).exists()

    def delete(self, *args, **kwargs):
        raise ValidationError("Users are never deleted. Set is_active = False instead.")


class Role(models.Model):
    """One of the eight Phase 3 roles (data dictionary: Role)."""

    id = models.BigAutoField(primary_key=True, db_column="roleId")
    name = models.CharField(max_length=40, unique=True, choices=RoleName.choices)

    class Meta:
        db_table = "Role"
        ordering = ["id"]
        constraints = [choices_check("name", RoleName, "role_name_valid")]

    def __str__(self):
        return self.get_name_display()


class UserRole(models.Model):
    """Who holds which role. Primary key (userId, roleId); a user may hold several roles."""

    pk = models.CompositePrimaryKey("user", "role")
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column="userId")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, db_column="roleId")
    assigned_at = models.DateTimeField(auto_now_add=True, db_column="assignedAt")

    class Meta:
        db_table = "UserRole"

    def __str__(self):
        return f"{self.user_id} - {self.role}"


class InsertOnlyModel(models.Model):
    """Base for append-only records (BR-14): rows are added, never changed or deleted.

    Prototype 1 enforces this in the application; the database-level
    insert-only permission is a later increment (data dictionary, AuditLog).
    """

    #: fields that may still be filled in once after the row exists
    UPDATABLE_ONCE = ()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            update_fields = kwargs.get("update_fields")
            if not update_fields or not set(update_fields) <= set(self.UPDATABLE_ONCE):
                raise ValidationError(f"{type(self).__name__} rows are insert-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(f"{type(self).__name__} rows are insert-only and cannot be deleted.")


class AuditLog(InsertOnlyModel):
    """Who changed what and why (data dictionary: AuditLog). Insert only (BR-14).

    A mistake is fixed by adding a new event that points at the wrong one
    through correctsEventId, never by editing the old row.
    """

    id = models.BigAutoField(primary_key=True, db_column="eventId")
    user = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, blank=True, related_name="audit_events", db_column="userId"
    )
    corrects_event = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="corrections", db_column="correctsEventId"
    )
    action = models.CharField(max_length=60)
    record_type = models.CharField(max_length=60, db_column="recordType")
    record_id = models.BigIntegerField(db_column="recordId")
    before_value = models.JSONField(null=True, blank=True, db_column="beforeValue")
    after_value = models.JSONField(null=True, blank=True, db_column="afterValue")
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_column="createdAt")

    class Meta:
        db_table = "AuditLog"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["record_type", "record_id"], name="auditlog_record_idx"),
            models.Index(fields=["created_at"], name="auditlog_created_idx"),
        ]

    def __str__(self):
        return f"{self.action} {self.record_type}#{self.record_id}"
