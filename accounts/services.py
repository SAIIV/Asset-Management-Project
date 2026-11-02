"""AuditService: the one way to write to the audit log (Section 6.3).

    AuditService.log(user, "approve", record=approval, before={"decision": "Pending"},
                     after={"decision": "Approved"}, reason="...")

Rows are only ever added (BR-14). Passwords, API keys and full prompts are
never written here.
"""

from .models import AuditLog


class AuditService:
    @staticmethod
    def log(user, action, record=None, *, record_type=None, record_id=None,
            before=None, after=None, reason="", corrects=None):
        if record is not None:
            record_type = record_type or type(record).__name__
            record_id = record_id if record_id is not None else record.pk
        return AuditLog.objects.create(
            user=user if getattr(user, "is_authenticated", False) else None,
            action=action,
            record_type=record_type or "",
            record_id=record_id or 0,
            before_value=before,
            after_value=after,
            reason=reason,
            corrects_event=corrects,
        )
