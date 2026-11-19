"""C7 Sustainability dashboard: the Section 12 calculations.

A benefit is counted only for a completed event (a received permanent
transfer), never because an item was listed or approved. Each result is stored
in SustainabilityImpact with its inputs, so the dashboard can show how it was
calculated, and every number is recalculated from the database each time.

    record_transfer_impact(transfer)   -> one SustainabilityImpact for a received transfer
    sync_impacts()                     -> adds the rows still missing (safe to run any time)
    dashboard(start, end)              -> the figures, their formulas and the missing-data counts

Prototype 1 assumptions (shown on the page):
  * Replacement baseline = the asset's estimated value (AED). Synthetic, not finance-validated.
  * Transfer cost = 0, because Prototype 1 does not record it. Repairs are a later increment.
  * A loan adds nothing (Section 12 counting rule), so only Permanent transfers count.
  * Mass is the recorded massKg, not weighed again, so isMeasured stays false.
  * kg CO2e = (massKg / 907.185) x WARM factor (MTCO2E per short ton) x 1000.
    WARM_FACTORS below must be filled in from the EPA WARM tables the group uses;
    a category without a factor gets no CO2e (never a made-up default).
"""

from decimal import Decimal

from django.db.models import Count, Sum

from accounts.models import AuditLog
from circular_campus.choices import TransferStatus, TransferType
from transfers.models import Transfer

from .models import SustainabilityImpact

SHORT_TON_KG = Decimal("907.185")
WARM_VERSION = "EPA WARM v16"

#: Top category -> avoided emissions in MTCO2E per short ton (source reduction), from EPA WARM.
#: None = no factor entered yet, so CO2e is shown as unavailable for that category.
WARM_FACTORS = {
    "IT Equipment": None,
    "Lab Equipment": None,
    "Furniture": None,
}


def top_category(category):
    while category.parent_category_id is not None:
        category = category.parent_category
    return category


def co2e_for(mass_kg, category):
    """(kg CO2e, factor reference) or (None, reason) when it cannot be calculated."""
    top = top_category(category).name
    factor = WARM_FACTORS.get(top)
    if mass_kg is None:
        return None, "no mass recorded"
    if factor is None:
        return None, f"no {WARM_VERSION} factor entered for {top}"
    kg = (Decimal(mass_kg) / SHORT_TON_KG) * Decimal(str(factor)) * 1000
    return kg.quantize(Decimal("0.001")), f"{WARM_VERSION}, {top}, {factor} MTCO2E/short ton"


def record_transfer_impact(transfer):
    """Store the benefit of one received permanent transfer. Returns None when it does not count."""
    if transfer.status != TransferStatus.RECEIVED or transfer.type != TransferType.PERMANENT:
        return None
    existing = SustainabilityImpact.objects.filter(transfer=transfer).first()
    if existing:
        return existing
    asset = transfer.asset
    if asset.estimated_value_aed is None:
        return None  # no baseline -> no avoided purchase can be claimed
    co2e, reference = co2e_for(asset.mass_kg, asset.category)
    return SustainabilityImpact.objects.create(
        transfer=transfer,
        avoided_cost_aed=asset.estimated_value_aed - Decimal("0"),  # baseline - transfer cost (0 in Prototype 1)
        diverted_mass_kg=asset.mass_kg,
        co2e_kg=co2e,
        factor_ref=reference,
        is_measured=False,
    )


def sync_impacts():
    missing = (Transfer.objects.filter(status=TransferStatus.RECEIVED, type=TransferType.PERMANENT,
                                       impact__isnull=True)
               .select_related("asset__category__parent_category"))
    return [impact for impact in (record_transfer_impact(t) for t in missing) if impact]


def _in_period(queryset, field, start, end):
    if start:
        queryset = queryset.filter(**{f"{field}__date__gte": start})
    if end:
        queryset = queryset.filter(**{f"{field}__date__lte": end})
    return queryset


def dashboard(start=None, end=None):
    """Every figure of Mockup 6 with its formula, calculated from the database."""
    reused = _in_period(Transfer.objects.filter(status=TransferStatus.RECEIVED, type=TransferType.PERMANENT),
                        "received_at", start, end).select_related("asset__category__parent_category")
    impacts = SustainabilityImpact.objects.filter(transfer__in=reused)
    totals = impacts.aggregate(cost=Sum("avoided_cost_aed"), mass=Sum("diverted_mass_kg"), co2e=Sum("co2e_kg"),
                               events=Count("id"))
    reuse_count = reused.count()
    published = _in_period(AuditLog.objects.filter(action="publish_asset"), "created_at", start, end).order_by()
    published_assets = published.values("record_id").distinct().count()
    reused_published = reused.filter(asset_id__in=published.values("record_id")).values("asset_id").distinct().count()

    by_category = {}
    for transfer in reused:
        name = top_category(transfer.asset.category).name
        by_category[name] = by_category.get(name, 0) + 1
    largest = max(by_category.values(), default=0)

    return {
        "reuse_count": reuse_count,
        "avoided_aed": totals["cost"],
        "diverted_kg": totals["mass"],
        "co2e_kg": totals["co2e"],
        "reuse_rate": round(100 * reused_published / published_assets, 1) if published_assets else None,
        "published_assets": published_assets,
        "no_baseline": reuse_count - totals["events"],
        "no_mass": impacts.filter(diverted_mass_kg__isnull=True).count(),
        "no_co2e": impacts.filter(co2e_kg__isnull=True).count(),
        "by_category": [(name, n, round(100 * n / largest) if largest else 0)
                        for name, n in sorted(by_category.items(), key=lambda kv: -kv[1])],
        "impacts": impacts.select_related("transfer__asset", "transfer__request__requester__department")
                          .order_by("-transfer__received_at"),
        "warm_version": WARM_VERSION,
    }
