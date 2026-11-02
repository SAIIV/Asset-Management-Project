"""AI gateway records (stores D6 and D7): ModelVersion, AIRecord."""

from django.db import models
from django.db.models import Q

from accounts.models import InsertOnlyModel
from circular_campus.choices import AIDecision, AITask, ModelKind, choices_check


class ModelVersion(InsertOnlyModel):
    """Model, prompt, ranking weights and thresholds in use.

    Rows are never edited; a change adds a row with a new activeFrom (P3-NFR-Q11).
    """

    id = models.BigAutoField(primary_key=True, db_column="modelVersionId")
    kind = models.CharField(max_length=20, choices=ModelKind.choices)
    name = models.CharField(max_length=120)
    prompt_version = models.CharField(max_length=40, blank=True, db_column="promptVersion")
    weights = models.JSONField(default=dict, blank=True)
    thresholds = models.JSONField(default=dict, blank=True)
    active_from = models.DateTimeField(db_column="activeFrom")

    class Meta:
        db_table = "ModelVersion"
        ordering = ["-active_from"]
        constraints = [choices_check("kind", ModelKind, "modelversion_kind_valid")]

    def __str__(self):
        return f"{self.kind}: {self.name} (from {self.active_from:%Y-%m-%d})"


class AIRecord(InsertOnlyModel):
    """One AI call and the person's answer to it (Section 13).

    Insert only, except decision and overrideReason, which are filled once.
    """

    UPDATABLE_ONCE = ("decision", "override_reason")

    id = models.BigAutoField(primary_key=True, db_column="aiRecordId")
    model_version = models.ForeignKey(
        ModelVersion, on_delete=models.PROTECT, related_name="ai_records", db_column="modelVersionId"
    )
    task = models.CharField(max_length=30, choices=AITask.choices)
    input_refs = models.JSONField(default=dict, blank=True, db_column="inputRefs")
    output = models.JSONField(default=dict, blank=True)
    score = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    unsure = models.BooleanField(default=False)
    fallback = models.BooleanField(default=False)
    latency_ms = models.PositiveIntegerField(null=True, blank=True, db_column="latencyMs")
    decision = models.CharField(max_length=20, choices=AIDecision.choices, null=True, blank=True)
    override_reason = models.TextField(blank=True, db_column="overrideReason")
    created_at = models.DateTimeField(auto_now_add=True, db_column="createdAt")

    class Meta:
        db_table = "AIRecord"
        ordering = ["-created_at"]
        constraints = [
            choices_check("task", AITask, "airecord_task_valid"),
            choices_check("decision", AIDecision, "airecord_decision_valid", allow_null=True),
        ]
        indexes = [models.Index(fields=["task", "created_at"], name="airecord_task_idx")]

    def save(self, *args, **kwargs):
        # decision / overrideReason may be filled once, never changed afterwards.
        if not self._state.adding and kwargs.get("update_fields"):
            stored = type(self).objects.filter(pk=self.pk).values("decision").first()
            if stored and stored["decision"]:
                from django.core.exceptions import ValidationError
                raise ValidationError("The decision on this AI record was already recorded.")
        super().save(*args, **kwargs)
