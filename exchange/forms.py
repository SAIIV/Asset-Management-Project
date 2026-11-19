"""C4: the request form of Mockup 2 (UC-10 Submit, UC-11 Revise)."""

from django import forms
from django.utils import timezone

from assets.models import Asset
from circular_campus.choices import Condition, TransferType, Urgency


class RequestForm(forms.Form):
    purpose = forms.CharField(label="Purpose", widget=forms.Textarea(attrs={"rows": 3}), max_length=2000,
                              help_text="What the items are for, e.g. second screens for the new teaching lab.")
    quantity = forms.IntegerField(label="Quantity", min_value=1, max_value=500, initial=1)
    required_by = forms.DateField(label="Required by", widget=forms.DateInput(attrs={"type": "date"}))
    urgency = forms.ChoiceField(label="Urgency", choices=Urgency.choices, initial=Urgency.NORMAL)
    type = forms.ChoiceField(label="Type", choices=[(TransferType.PERMANENT, "Permanent transfer"),
                                                    (TransferType.LOAN, "Loan")],
                             initial=TransferType.PERMANENT)
    mandatory_specs_text = forms.CharField(label="Mandatory specifications", required=False, max_length=1000,
                                           help_text="Separate with commas, e.g. HDMI input, at least 22 inch")
    preferred_condition = forms.ChoiceField(label="Preferred condition", required=False,
                                            choices=[("", "Any")] + list(Condition.choices))
    candidates = forms.ModelMultipleChoiceField(
        label="Candidate assets (optional)", required=False, queryset=Asset.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        help_text="Items from the catalogue you would like. Leave empty if you have not chosen yet.",
    )

    def __init__(self, *args, eligible=None, **kwargs):
        super().__init__(*args, **kwargs)
        if eligible is not None:
            self.fields["candidates"].queryset = eligible
        self.fields["candidates"].label_from_instance = (
            lambda a: f"{a.name} · {a.get_condition_display()} · {a.owner_department.name}")

    def clean_required_by(self):
        value = self.cleaned_data["required_by"]
        if value < timezone.localdate():
            raise forms.ValidationError("The required-by date cannot be in the past.")
        return value

    def clean(self):
        data = super().clean()
        specs = data.get("mandatory_specs_text") or ""
        data["mandatory_specs"] = [s.strip() for s in specs.split(",") if s.strip()]
        candidates = data.get("candidates") or []
        if data.get("quantity") and len(candidates) > data["quantity"]:
            self.add_error("candidates", f"Choose at most {data['quantity']} asset(s), the quantity you asked for.")
        return data


class CancelForm(forms.Form):
    reason = forms.CharField(label="Reason", required=False, max_length=300)
