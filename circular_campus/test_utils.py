"""Small helpers that build valid test records, shared by every app's tests."""

from datetime import date, timedelta
from itertools import count

from django.utils import timezone

_n = count(1)


def make_department(**kw):
    from assets.models import Department
    return Department.objects.create(name=kw.pop("name", f"Test Dept {next(_n)}"), **kw)


def make_category(**kw):
    from assets.models import Category
    return Category.objects.create(name=kw.pop("name", f"Test Category {next(_n)}"), **kw)


def make_asset(model=None, **kw):
    """An Asset (or ITAsset / LabEquipment / FurnitureAsset when model is given)."""
    from assets.models import Asset
    model = model or Asset
    kw.setdefault("name", f"Test asset {next(_n)}")
    kw.setdefault("condition", "Good")
    if "owner_department" not in kw:
        kw["owner_department"] = make_department()
    if "category" not in kw:
        kw["category"] = make_category()
    return model.objects.create(**kw)


def make_user(**kw):
    from accounts.models import User
    n = next(_n)
    return User.objects.create_user(
        kw.pop("email", f"user{n}@test.example"), "Test-pass-123", name=kw.pop("name", f"Test User {n}"), **kw
    )


def make_request(requester=None, **kw):
    from exchange.models import ResourceRequest
    kw.setdefault("required_by", date.today() + timedelta(days=14))
    return ResourceRequest.objects.create(requester=requester or make_user(), **kw)


def now():
    return timezone.now()
