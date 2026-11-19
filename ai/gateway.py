"""AI gateway: model versions (D6) and AI records (D7), Design Document Section 13.

    model_version(kind, name, prompt_version, thresholds) -> the ModelVersion in use
    record(version, task, ...)                            -> one insert-only AIRecord
    record_decision(record_id, task, decision, reason)    -> the person's answer, filled once

Every AI result is stored with the model, prompt version and thresholds that
produced it, so results from different settings are never mixed (P3-NFR-Q11).
"""

from django.utils import timezone

from .models import AIRecord, ModelVersion


def model_version(kind, name, prompt_version="", weights=None, thresholds=None):
    """The current row for these settings. A change adds a new row; old rows are never edited."""
    weights, thresholds = weights or {}, thresholds or {}
    current = ModelVersion.objects.filter(kind=kind, name=name).order_by("-active_from", "-id").first()
    if (current and current.prompt_version == prompt_version and current.weights == weights
            and current.thresholds == thresholds):
        return current
    return ModelVersion.objects.create(kind=kind, name=name, prompt_version=prompt_version, weights=weights,
                                       thresholds=thresholds, active_from=timezone.now())


def record(version, task, *, input_refs=None, output=None, score=None, unsure=False, fallback=False,
           latency_ms=None):
    return AIRecord.objects.create(model_version=version, task=task, input_refs=input_refs or {},
                                   output=output or {}, score=score, unsure=unsure, fallback=fallback,
                                   latency_ms=latency_ms)


def record_decision(record_id, task, decision, reason=""):
    """Store Accepted, Corrected or Rejected once. Returns the record, or None if it cannot be answered."""
    item = AIRecord.objects.filter(pk=record_id, task=task, decision__isnull=True, fallback=False).first()
    if item is None:
        return None
    item.decision, item.override_reason = decision, reason
    item.save(update_fields=["decision", "override_reason"])
    return item
