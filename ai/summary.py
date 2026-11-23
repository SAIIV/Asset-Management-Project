"""AI #5 Generated report summary (Design Document Section 4 service 6, 10.2 draft_summary; UC-38).

    draft_summary(kind, facts)                           -> Draft (text + number check), or "unavailable"
    publish_summary(user, kind, record_id, text, facts)  -> the checked text, kept in the audit log
    discard_summary(user, record_id)                     -> the officer threw the draft away
    latest_published(kind)                               -> the last published summary of that report

Rules kept here:
  * The numbers and charts always come from the database; the AI only writes words around them.
  * Every number in the draft must equal a number in the report (numbersUsed is checked too).
    Any other number blocks publishing (P3-XR-06), also after the officer edits the text.
  * Nothing is published by the AI: a person presses Publish (gate 8). Publish without edits
    = Accepted, after edits = Corrected, Discard = Rejected (Section 13).
  * If the service is off, slow or answers in the wrong shape: "Draft summary unavailable";
    the report itself works as normal.
"""

import re
import time
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from accounts.models import AuditLog
from accounts.services import AuditService
from circular_campus.choices import AIDecision, AITask, ModelKind

from .gateway import model_version, record, record_decision
from .generators import AIUnavailable, SchemaMismatch, get_generator

PROMPT_VERSION = "summary v2"
TIME_LIMIT = 30  # seconds (Section 4)
SCHEMA = {
    "type": "OBJECT",
    "properties": {"text": {"type": "STRING"}, "numbersUsed": {"type": "ARRAY", "items": {"type": "NUMBER"}}},
    "required": ["text", "numbersUsed"],
}
NUMBER = re.compile(r"(?<![\w.])\d+(?:,\d{3})*(?:\.\d+)?")  # 4,800 yes; the comma after it no


class SummaryError(Exception):
    """Publishing was blocked; the message is shown to the user."""


@dataclass
class Draft:
    record_id: int | None = None
    text: str = ""
    checks: list = field(default_factory=list)  # [(number as written, True if it is in the report)]
    fallback: bool = False
    message: str = ""
    model: str = ""

    @property
    def matched(self):
        return sum(1 for _, ok in self.checks if ok)

    @property
    def ok(self):
        return bool(self.text) and all(ok for _, ok in self.checks)

    @property
    def wrong(self):
        return [number for number, ok in self.checks if not ok]


def plain(value):
    """Decimal -> int or float, so the facts are plain JSON numbers."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    return value


def _decimal(text):
    try:
        return Decimal(str(text).replace(",", "").rstrip("."))
    except InvalidOperation:
        return None


def fact_numbers(facts):
    """Every number in the facts (dates are text, so a date written in the summary is not accepted)."""
    found = set()
    if isinstance(facts, bool) or facts is None:
        return found
    if isinstance(facts, (int, float, Decimal)):
        found.add(_decimal(facts))
    elif isinstance(facts, dict):
        for value in facts.values():
            found |= fact_numbers(value)
    elif isinstance(facts, (list, tuple)):
        for value in facts:
            found |= fact_numbers(value)
    return {n for n in found if n is not None}


def check_numbers(text, facts, numbers_used=()):
    """[(number as written, True if it equals a figure of the report)], each number once."""
    allowed = fact_numbers(facts)
    written = [m.group(0) for m in NUMBER.finditer(text)] + [str(n) for n in numbers_used]
    checks, seen = [], set()
    for raw in written:
        value = _decimal(raw)
        if value is None or value in seen:
            continue
        seen.add(value)
        checks.append((raw, value in allowed))
    return checks


def draft_summary(kind, facts):
    started = time.monotonic()
    failure = None
    try:
        generator = get_generator()
        name = generator.name
    except AIUnavailable as error:
        generator, name, failure = None, "not configured", error
    version = model_version(ModelKind.TEXT_GENERATION, name, PROMPT_VERSION)
    inputs = {"report": kind, "facts": facts}
    try:
        if generator is None:
            raise failure
        result = generator.generate(AITask.DRAFT_SUMMARY.value, facts, SCHEMA, TIME_LIMIT)
    except AIUnavailable as error:
        unsure = isinstance(error, SchemaMismatch)
        item = record(version, AITask.DRAFT_SUMMARY, input_refs=inputs, unsure=unsure, fallback=not unsure,
                      output={"error": str(error)}, latency_ms=int((time.monotonic() - started) * 1000))
        return Draft(record_id=item.pk, fallback=True, model=name,
                     message=f"Draft summary unavailable: {error}. The figures and tables are not affected.")

    text = str(result.get("text", "")).strip()
    numbers_used = [n for n in result.get("numbersUsed") or [] if isinstance(n, (int, float))]
    draft = Draft(text=text, checks=check_numbers(text, facts, numbers_used), model=name)
    item = record(version, AITask.DRAFT_SUMMARY, input_refs=inputs, unsure=not draft.ok,
                  score=(Decimal(draft.matched) / len(draft.checks)).quantize(Decimal("0.001"))
                  if draft.checks else None,
                  latency_ms=int((time.monotonic() - started) * 1000),
                  output={"text": text, "numbersUsed": numbers_used, "wrong": draft.wrong})
    draft.record_id = item.pk
    return draft


def publish_summary(user, kind, record_id, text, facts):
    """Gate 8: a person publishes the (possibly edited) draft. Blocked if any number is not in the report."""
    from .models import AIRecord

    item = AIRecord.objects.filter(pk=record_id, task=AITask.DRAFT_SUMMARY, fallback=False,
                                   decision__isnull=True).first()
    if item is None:
        raise SummaryError("This draft was already published or discarded. Draft a new one.")
    text = (text or "").strip()
    if not text:
        raise SummaryError("The summary is empty.")
    wrong = [number for number, ok in check_numbers(text, facts) if not ok]
    if wrong:
        raise SummaryError(f"Publishing blocked: {', '.join(wrong)} is not a figure of this report. "
                           f"Correct the number or remove it.")
    edited = text != item.output.get("text", "")
    record_decision(item.pk, AITask.DRAFT_SUMMARY, AIDecision.CORRECTED if edited else AIDecision.ACCEPTED,
                    "edited by the officer before publishing" if edited else "")
    AuditService.log(user, "publish_summary", record_type="Report", record_id=item.pk,
                     after={"kind": kind, "text": text, "edited": edited, "model": item.model_version.name})
    return text


def discard_summary(user, record_id, reason=""):
    return record_decision(record_id, AITask.DRAFT_SUMMARY, AIDecision.REJECTED, reason or "discarded")


def latest_published(kind):
    row = (AuditLog.objects.filter(action="publish_summary", after_value__kind=kind)
           .select_related("user").order_by("-created_at", "-id").first())
    if row is None:
        return None
    return {"text": row.after_value.get("text", ""), "by": row.user, "at": row.created_at,
            "edited": row.after_value.get("edited", False), "model": row.after_value.get("model", "")}
