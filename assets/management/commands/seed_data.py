"""Fill an empty database with SYNTHETIC test data.

    python manage.py seed_data             # departments, categories, assets, users
    python manage.py seed_data --history   # ... plus a few requests run through the real workflow

Creates the 8 roles, 5 fictional departments, a small category tree, about 50
synthetic assets (IT, lab and furniture) and 4 test users, one per Prototype 1
role. Every record is invented and marked "synthetic", so no real staff or
asset data is ever stored or sent to the Gemini API (Phase 6 plan, Section 2).

--history also sends 8 synthetic requests through the real services (request,
reserve, approve, release, receive), so the dashboard, reports, inboxes and the
AI summary have something to show: permanent transfers received, one in
transit, one waiting for approval, one waiting for the custodian and a loan.
Every listed seed asset also gets its "publish_asset" audit row (by the system),
which the reuse rate needs.

Running it twice is safe: existing records are found and reused, not copied.
"""

import os
import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import AuditLog, Role, User, UserRole
from accounts.services import AuditService
from assets.models import Asset, Category, Department, FurnitureAsset, ITAsset, LabEquipment
from circular_campus.choices import (
    ApprovalDecision,
    AssetStatus,
    Condition,
    RequestStatus,
    RoleName,
    TransferStatus,
    TransferType,
)

SYNTHETIC_TAG = "synthetic"
EMAIL_DOMAIN = "circular-campus.example"   # .example is reserved and can never be a real address

DEPARTMENTS = [
    ("Mechanical Engineering (Synthetic)", "Building 3"),
    ("Computer Science (Synthetic)", "Building 5"),
    ("Chemistry (Synthetic)", "Building 2"),
    ("Student Services (Synthetic)", "Building 1"),
    ("Facilities Management (Synthetic)", "Building 7"),
]

# (top category, [sub-categories]) - the tree that AI #1 classifies into.
CATEGORIES = [
    ("IT Equipment", ["Laptops", "Monitors", "Printers"]),
    ("Lab Equipment", ["Microscopes", "Centrifuges", "Balances"]),
    ("Furniture", ["Chairs", "Desks", "Cabinets"]),
]

# Item templates per sub-category: (name, estimated value AED, mass kg, extra)
IT_ITEMS = {
    "Laptops": [("Dell Latitude 5420 laptop", 2100, 1.4), ("Lenovo ThinkPad T14 laptop", 2400, 1.5)],
    "Monitors": [("Dell P2419H 24-inch monitor", 450, 5.0), ("HP E24 G4 24-inch monitor", 520, 4.8)],
    "Printers": [("HP LaserJet Pro M404 printer", 900, 8.6)],
}
LAB_ITEMS = {
    "Microscopes": [("Olympus CX23 student microscope", 3200, 6.5)],
    "Centrifuges": [("Eppendorf 5424 micro-centrifuge", 7800, 15.0)],
    "Balances": [("Ohaus Pioneer analytical balance", 4100, 4.9)],
}
FURNITURE_ITEMS = {
    "Chairs": [("Ergonomic office chair", 650, 14.0, "Mesh and steel"), ("Stacking classroom chair", 120, 5.5, "Polypropylene")],
    "Desks": [("Height-adjustable desk", 1500, 38.0, "Steel and laminate"), ("Student writing desk", 300, 18.0, "Wood")],
    "Cabinets": [("Four-drawer filing cabinet", 700, 42.0, "Steel")],
}

TEST_USERS = [
    (RoleName.REQUESTER, "Synthetic Requester", "requester", 1),
    (RoleName.CUSTODIAN, "Synthetic Custodian", "custodian", 0),
    (RoleName.APPROVER, "Synthetic Approver", "approver", 1),
    (RoleName.ADMINISTRATOR, "Synthetic Administrator", "admin", 4),
]

ASSET_COUNT = 50
STATUS_MIX = [AssetStatus.AVAILABLE] * 6 + [AssetStatus.DRAFT, AssetStatus.IN_USE, AssetStatus.UNDER_MAINTENANCE]
CONDITION_MIX = [Condition.NEW, Condition.GOOD, Condition.GOOD, Condition.GOOD, Condition.FAIR, Condition.NEEDS_REPAIR]


HISTORY_MARK = "SYNTHETIC demo history"
# (how far the request gets, request type, purpose) - one unit each, in this order. If the custodian's
# department has fewer Available units than steps, the last steps are skipped.
HISTORY = [
    (TransferStatus.RECEIVED, TransferType.PERMANENT, "replace worn-out equipment in a teaching lab"),
    (RequestStatus.UNDER_REVIEW, TransferType.PERMANENT, "spare unit for exam week"),
    (TransferStatus.RECEIVED, TransferType.PERMANENT, "equip a new research assistant"),
    (RequestStatus.SUBMITTED, TransferType.PERMANENT, "extra unit for a summer course"),
    (TransferStatus.RECEIVED, TransferType.PERMANENT, "set up a student help desk"),
    (TransferStatus.DISPATCHED, TransferType.PERMANENT, "second workstation for the lab"),
    (TransferStatus.RECEIVED, TransferType.PERMANENT, "furnish a shared project room"),
    (TransferStatus.RECEIVED, TransferType.LOAN, "short loan for an open day"),
]


class Command(BaseCommand):
    help = "Create synthetic departments, categories, assets and 4 test users (safe to run twice)."

    def add_arguments(self, parser):
        parser.add_argument("--history", action="store_true",
                            help="Also run 8 synthetic requests through the workflow (for demos).")

    @transaction.atomic
    def handle(self, *args, **options):
        rng = random.Random(336)  # fixed seed: everyone gets the same data
        password = os.environ.get("SEED_USER_PASSWORD") or "Synthetic-Demo-2026"

        roles = {name: Role.objects.get_or_create(name=name)[0] for name in RoleName.values}
        departments = [
            Department.objects.get_or_create(name=name, defaults={"building": building})[0]
            for name, building in DEPARTMENTS
        ]

        categories = {}
        for top_name, children in CATEGORIES:
            top, _ = Category.objects.get_or_create(
                name=top_name, defaults={"description": f"{top_name} (top category, synthetic test data)"}
            )
            for child in children:
                categories[child], _ = Category.objects.get_or_create(
                    name=child, defaults={"parent_category": top, "description": f"{child} (synthetic test data)"}
                )

        created = self._create_assets(rng, departments, categories)

        for role_name, full_name, local_part, dept_index in TEST_USERS:
            user, new = User.objects.get_or_create(
                email=f"{local_part}@{EMAIL_DOMAIN}",
                defaults={"name": full_name, "department": departments[dept_index]},
            )
            if new:
                user.set_password(password)
                if role_name == RoleName.ADMINISTRATOR:
                    user.is_staff = user.is_superuser = True  # may open /admin/
                user.save()
            UserRole.objects.get_or_create(user=user, role=roles[role_name])

        self.stdout.write(self.style.SUCCESS(
            f"Synthetic data ready: {Role.objects.count()} roles, {Department.objects.count()} departments, "
            f"{Category.objects.count()} categories, {Asset.objects.count()} assets ({created} new), "
            f"{User.objects.count()} users."
        ))
        self.stdout.write(f"Test users (password: {password}):")
        for role_name, _, local_part, _ in TEST_USERS:
            self.stdout.write(f"  {role_name:<14} {local_part}@{EMAIL_DOMAIN}")
        if options.get("history"):
            self.stdout.write(self._create_history(departments))

    def _create_history(self, departments):
        """Run the HISTORY requests through the real C4/C5 services, so every rule and audit row applies."""
        from exchange.models import RequestSpecification
        from exchange.requests import RequestService
        from transfers.models import Transfer
        from transfers.services import TransferService

        if RequestSpecification.objects.filter(purpose__startswith=HISTORY_MARK).exists():
            return "Demo history already exists: nothing added."

        for asset in Asset.objects.filter(tags__contains=[SYNTHETIC_TAG], is_listed=True):
            if not AuditLog.objects.filter(action="publish_asset", record_id=asset.pk).exists():
                AuditService.log(None, "publish_asset", asset, reason="listed by seed_data (synthetic test data)")

        users = {local: User.objects.get(email=f"{local}@{EMAIL_DOMAIN}") for _, _, local, _ in TEST_USERS}
        requester, custodian, approver = users["requester"], users["custodian"], users["approver"]
        units = list(Asset.objects.filter(owner_department=custodian.department, status=AssetStatus.AVAILABLE,
                                          is_listed=True, tags__contains=[SYNTHETIC_TAG]).order_by("pk"))
        steps = list(zip(HISTORY, units))
        for (goal, kind, purpose), asset in steps:
            request = RequestService.create(requester, {
                "purpose": f"{HISTORY_MARK}: {purpose}", "quantity": 1,
                "required_by": date.today() + timedelta(days=14), "urgency": "Normal", "type": kind,
                "mandatory_specs": [], "preferred_condition": "", "candidates": [asset],
            })
            if goal == RequestStatus.SUBMITTED:
                continue
            TransferService.reserve(custodian, request, [asset])
            if goal == RequestStatus.UNDER_REVIEW:
                continue
            TransferService.decide(approver, request, ApprovalDecision.APPROVED, "synthetic demo history")
            transfer = Transfer.objects.get(request=request, asset=asset)
            TransferService.release(custodian, transfer)
            if goal == TransferStatus.RECEIVED:
                TransferService.receive(requester, transfer, asset.condition)
        return (f"Demo history: {len(steps)} requests from {requester.department} to {custodian.department} "
                f"({sum(1 for (g, _, _), _ in steps if g == TransferStatus.RECEIVED)} received). "
                f"Open the Sustainability dashboard as {users['admin'].email} to see the figures.")

    def _create_assets(self, rng, departments, categories):
        existing = Asset.objects.filter(tags__contains=[SYNTHETIC_TAG]).count()
        if existing >= ASSET_COUNT:
            return 0

        kinds = (
            [("it", sub, item) for sub, items in IT_ITEMS.items() for item in items]
            + [("lab", sub, item) for sub, items in LAB_ITEMS.items() for item in items]
            + [("furniture", sub, item) for sub, items in FURNITURE_ITEMS.items() for item in items]
        )
        # Skip the random numbers already used, so a second run continues the same sequence.
        for _ in range(existing):
            rng.random()

        created = 0
        for number in range(existing + 1, ASSET_COUNT + 1):
            kind, sub, item = kinds[(number - 1) % len(kinds)]
            name, value, mass = item[0], item[1], item[2]
            status = rng.choice(STATUS_MIX)
            department = departments[(number - 1) % len(departments)]
            common = {
                "name": f"{name} (synthetic #{number:03d})",
                "description": f"SYNTHETIC test record #{number:03d}. {name} for Circular Campus development.",
                "owner_department": department,
                "category": categories[sub],
                "condition": rng.choice(CONDITION_MIX),
                "status": status,
                "is_listed": status == AssetStatus.AVAILABLE,
                "campus": "Main Campus (synthetic)",
                "building": department.building,
                "room": f"{rng.randint(1, 3)}{rng.randint(0, 2)}{rng.randint(1, 9)}",
                "purchase_date": date(2026, 9, 1) - timedelta(days=rng.randint(200, 2500)),
                "estimated_value_aed": Decimal(value) * Decimal(rng.choice(["0.4", "0.5", "0.6", "0.7"])),
                "mass_kg": Decimal(str(mass)),
                "tags": [SYNTHETIC_TAG, sub.lower()],
            }
            if kind == "it":
                ITAsset.objects.create(serial_number=f"SYN-IT-{number:04d}", **common)
            elif kind == "lab":
                LabEquipment.objects.create(
                    calibration_due=date(2026, 11, 1) + timedelta(days=rng.randint(-60, 300)), **common
                )
            else:
                FurnitureAsset.objects.create(material=item[3], **common)
            created += 1
        return created
