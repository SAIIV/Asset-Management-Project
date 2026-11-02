"""Reporting & Sustainability (store D5): SustainabilityImpact."""

from django.db import models
from django.db.models import Q


class SustainabilityImpact(models.Model):
    """Benefit of one completed reuse (transfer) or repair (maintenance), Section 12.

    Exactly one of transferId or maintenanceId; avoidedCostAED may be negative;
    co2eKg stays empty when no WARM factor fits.
    """

    id = models.BigAutoField(primary_key=True, db_column="impactId")
    transfer = models.OneToOneField(
        "transfers.Transfer", on_delete=models.PROTECT, null=True, blank=True, related_name="impact",
        db_column="transferId",
    )
    maintenance = models.OneToOneField(
        "assets.MaintenanceRecord", on_delete=models.PROTECT, null=True, blank=True, related_name="impact",
        db_column="maintenanceId",
    )
    avoided_cost_aed = models.DecimalField(max_digits=12, decimal_places=2, db_column="avoidedCostAED")
    diverted_mass_kg = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True, db_column="divertedMassKg"
    )
    co2e_kg = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, db_column="co2eKg")
    factor_ref = models.CharField(max_length=200, blank=True, db_column="factorRef")
    is_measured = models.BooleanField(default=False, db_column="isMeasured")

    class Meta:
        db_table = "SustainabilityImpact"
        constraints = [
            models.CheckConstraint(
                condition=(Q(transfer__isnull=False, maintenance__isnull=True)
                           | Q(transfer__isnull=True, maintenance__isnull=False)),
                name="impact_exactly_one_source",
            ),
            models.CheckConstraint(
                condition=Q(diverted_mass_kg__isnull=True) | Q(diverted_mass_kg__gte=0),
                name="impact_mass_not_negative",
            ),
        ]
