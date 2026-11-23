"""AI gateway records (stores D6 and D7): ModelVersion, AIRecord.
Assistant (AI #4) conversations: AssistantChat, AssistantMessage, AssistantMemory."""

from django.conf import settings
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


# ---------------------------------------------------------------- AI #4 assistant conversations
# Each user has their own chats and memory; nobody else can open them (views filter by user).

class AssistantChat(models.Model):
    """One conversation of one user with the assistant."""

    id = models.BigAutoField(primary_key=True, db_column="chatId")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assistant_chats",
                             db_column="userId")
    title = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_column="createdAt")
    updated_at = models.DateTimeField(auto_now=True, db_column="updatedAt")

    class Meta:
        db_table = "AssistantChat"
        ordering = ["-updated_at", "-id"]
        indexes = [models.Index(fields=["user", "updated_at"], name="assistantchat_user_idx")]

    def __str__(self):
        return self.title or f"Chat {self.pk}"


def _chat_photo_path(message, filename):
    return f"assistant/{message.chat.user_id}/{message.chat_id}/{filename}"


class AssistantMessage(models.Model):
    """One turn: the user's question (with an optional photo) or the assistant's answer."""

    USER, ASSISTANT = "user", "assistant"
    ROLES = [(USER, "User"), (ASSISTANT, "Assistant")]

    id = models.BigAutoField(primary_key=True, db_column="messageId")
    chat = models.ForeignKey(AssistantChat, on_delete=models.CASCADE, related_name="messages", db_column="chatId")
    role = models.CharField(max_length=10, choices=ROLES)
    text = models.TextField(blank=True)
    photo = models.FileField(upload_to=_chat_photo_path, blank=True, max_length=300)
    items = models.JSONField(default=list, blank=True)   # [{"id", "name", "dept"}] cited catalogue items
    page = models.JSONField(null=True, blank=True)       # ["label", "url"] suggested page
    fallback = models.BooleanField(default=False)        # the AI was unavailable; text is the reason
    ai_record = models.ForeignKey(AIRecord, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name="assistant_messages", db_column="aiRecordId")
    rating = models.CharField(max_length=12, blank=True)  # "Helpful" / "Not helpful"
    created_at = models.DateTimeField(auto_now_add=True, db_column="createdAt")

    class Meta:
        db_table = "AssistantMessage"
        ordering = ["created_at", "id"]
        constraints = [models.CheckConstraint(condition=Q(role__in=["user", "assistant"]),
                                              name="assistantmessage_role_valid")]


class AssistantMemory(models.Model):
    """Short notes the assistant keeps about one user's needs, shown to them and clearable."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True,
                                related_name="assistant_memory", db_column="userId")
    notes = models.JSONField(default=list, blank=True)  # newest last, at most MEMORY_LIMIT entries
    updated_at = models.DateTimeField(auto_now=True, db_column="updatedAt")

    class Meta:
        db_table = "AssistantMemory"
