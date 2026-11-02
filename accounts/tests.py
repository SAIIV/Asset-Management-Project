"""Tests for the accounts tables: User, Role, UserRole, AuditLog."""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase

from accounts.models import AuditLog, Role, User, UserRole
from circular_campus.test_utils import make_department, make_user

# The 26 tables of Design Document Section 9, with their exact names.
SECTION_9_TABLES = {
    "User", "Role", "UserRole", "Department", "Asset", "ITAsset", "LabEquipment", "FurnitureAsset",
    "AssetCollection", "AssetCollectionItem", "Attachment", "Category", "ResourceRequest",
    "RequestSpecification", "MatchRecommendation", "ModelVersion", "Reservation", "Approval", "Transfer",
    "Inspection", "MaintenanceRecord", "LifecycleAction", "SustainabilityImpact", "Notification",
    "AuditLog", "AIRecord",
}

# The main rules of the data dictionary, as constraint names in PostgreSQL.
MAIN_CONSTRAINTS = {
    "Reservation": ["one_active_reservation_per_asset"],
    "Approval": ["approval_exactly_one_target", "approval_decision_valid"],
    "ResourceRequest": ["request_quantity_at_least_one", "request_status_valid", "request_urgency_valid"],
    "Asset": ["asset_condition_valid", "asset_status_valid", "asset_mass_positive_or_empty",
              "asset_embedding_hnsw_idx", "asset_status_listed_idx"],
    "MatchRecommendation": ["match_score_0_to_100"],
    "MaintenanceRecord": ["maintenance_cost_not_negative", "maintenance_completed_at_only_when_completed"],
    "LifecycleAction": ["lifecycle_executed_needs_evidence"],
    "SustainabilityImpact": ["impact_exactly_one_source"],
    "AssetCollectionItem": ["collection_item_unique"],
    "Attachment": ["attachment_one_per_kind"],
    "FurnitureAsset": ["furniture_material_required"],
    "Transfer": ["transfer_status_valid", "transfer_received_has_time"],
}


class SchemaTests(TestCase):
    """The database really contains the tables and constraints of Section 9."""

    def test_all_26_tables_exist_with_exact_names(self):
        tables = set(connection.introspection.table_names())
        self.assertEqual(len(SECTION_9_TABLES), 26)
        self.assertEqual(SECTION_9_TABLES - tables, set(), "missing tables")

    def test_main_constraints_and_indexes_exist(self):
        with connection.cursor() as cursor:
            for table, names in MAIN_CONSTRAINTS.items():
                found = connection.introspection.get_constraints(cursor, table)
                for name in names:
                    self.assertIn(name, found, f"{table} is missing {name}")

    def test_pgvector_extension_is_installed(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            self.assertIsNotNone(cursor.fetchone())

    def test_exact_column_names(self):
        with connection.cursor() as cursor:
            columns = {c.name for c in connection.introspection.get_table_description(cursor, "Asset")}
        for name in ["assetId", "ownerDepartmentId", "categoryId", "estimatedValueAED", "massKg", "isListed"]:
            self.assertIn(name, columns)


class UserTests(TestCase):
    def test_email_is_unique(self):
        make_user(email="same@test.example")
        with self.assertRaises(IntegrityError):
            make_user(email="same@test.example")

    def test_only_password_hash_is_stored(self):
        user = make_user()
        self.assertNotEqual(user.password, "Test-pass-123")
        self.assertTrue(user.password.startswith("pbkdf2_sha256$"))
        self.assertTrue(user.check_password("Test-pass-123"))

    def test_users_are_deactivated_not_deleted(self):
        user = make_user()
        with self.assertRaises(ValidationError):
            user.delete()

    def test_user_can_hold_several_roles_but_not_twice(self):
        user = make_user()
        requester = Role.objects.create(name="Requester")
        approver = Role.objects.create(name="Approver")
        UserRole.objects.create(user=user, role=requester)
        UserRole.objects.create(user=user, role=approver)
        self.assertTrue(user.has_role("Approver"))
        with self.assertRaises(IntegrityError):
            UserRole.objects.create(user=user, role=requester)

    def test_role_name_must_be_one_of_the_eight_roles(self):
        with self.assertRaises(IntegrityError):
            Role.objects.create(name="Superhero")


class AuditLogTests(TestCase):
    def test_audit_log_is_insert_only(self):
        event = AuditLog.objects.create(action="create", record_type="Asset", record_id=1)
        event.reason = "changed"
        with self.assertRaises(ValidationError):
            event.save()
        with self.assertRaises(ValidationError):
            event.delete()

    def test_a_correction_is_a_new_event(self):
        wrong = AuditLog.objects.create(action="update", record_type="Asset", record_id=1)
        fix = AuditLog.objects.create(action="correct", record_type="Asset", record_id=1, corrects_event=wrong)
        self.assertEqual(list(wrong.corrections.all()), [fix])


class BaseTemplateTests(TestCase):
    def test_base_template_shows_signed_in_role(self):
        user = make_user(name="Mona Custodian", department=make_department(name="Chemistry (Synthetic)"))
        UserRole.objects.create(user=user, role=Role.objects.create(name="Custodian"))
        request = RequestFactory().get("/")
        request.user = user
        html = render_to_string("base.html", {"user": user}, request=request)
        self.assertIn("css/circular.css", html)
        self.assertIn("Mona Custodian", html)
        self.assertIn('<span class="role">Custodian</span>', html)
        self.assertIn("MC", html)

    def test_base_template_when_signed_out(self):
        from django.contrib.auth.models import AnonymousUser
        html = render_to_string("base.html", {"user": AnonymousUser()})
        self.assertIn("Not signed in", html)
