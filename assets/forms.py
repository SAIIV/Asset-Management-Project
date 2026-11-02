"""C2: the asset form used by Register (UC-04) and Edit (UC-05).

The form checks each field and gives a clear message (UC-04 alternative:
"mandatory field missing or negative value"). The database constraints from
step 3 still check the same rules underneath.
"""

from datetime import date
from decimal import Decimal

from django import forms

from circular_campus.choices import AssetStatus

from .models import Asset, Category, ITAsset
from .services import KIND_LABELS, START_STATUSES


class AssetForm(forms.ModelForm):
    kind = forms.ChoiceField(label="Asset type", choices=list(KIND_LABELS.items()))
    status = forms.ChoiceField(
        label="Starting status",
        choices=[(s.value, s.label) for s in START_STATUSES],
        initial=AssetStatus.DRAFT,
        help_text="Draft: not ready yet. Available: can be shared. In use: used by your department.",
    )
    tags_text = forms.CharField(
        label="Tags", required=False, help_text="Separate tags with commas, e.g. laptop, 16GB, portable"
    )
    estimated_value_aed = forms.DecimalField(
        label="Estimated value (AED)", required=False, min_value=Decimal("0"), max_digits=12, decimal_places=2
    )
    mass_kg = forms.DecimalField(
        label="Mass (kg)", required=False, min_value=Decimal("0.001"), max_digits=10, decimal_places=3,
        help_text="Leave empty if unknown. Used later for the waste-diverted figure.",
    )
    # Subtype details: only the ones for the chosen type are required.
    serial_number = forms.CharField(label="Serial number (IT)", required=False, max_length=100)
    calibration_due = forms.DateField(
        label="Calibration due (lab)", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    material = forms.CharField(label="Material (furniture)", required=False, max_length=80)
    version = forms.IntegerField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = Asset
        fields = [
            "name", "description", "category", "condition", "campus", "building", "room",
            "purchase_date", "estimated_value_aed", "mass_kg",
        ]
        labels = {"name": "Asset name", "purchase_date": "Purchase date"}
        error_messages = {
            "name": {"required": "Enter the asset name."},
            "category": {"required": "Choose a category."},
            "condition": {"required": "Choose the condition."},
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "purchase_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, kind=None, details=None, **kwargs):
        """kind/details are given when editing: the type is then fixed."""
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.order_by("name")
        self.fields["category"].help_text = "The AI suggestion arrives with AI #1; for now choose from the list."
        self.editing = self.instance.pk is not None
        if self.editing:
            del self.fields["status"]  # status changes belong to C5/C6, not this form
            self.fields["kind"].disabled = True
            self.initial["kind"] = kind
            self.initial["tags_text"] = ", ".join(self.instance.tags)
            self.initial["version"] = self.instance.version
            if details is not None:
                for field in ("serial_number", "calibration_due", "material"):
                    if hasattr(details, field):
                        self.initial[field] = getattr(details, field)

    def clean_purchase_date(self):
        value = self.cleaned_data.get("purchase_date")
        if value and value > date.today():
            raise forms.ValidationError("The purchase date cannot be in the future.")
        return value

    def clean(self):
        data = super().clean()
        data["tags"] = [t.strip()[:40] for t in data.get("tags_text", "").split(",") if t.strip()]
        kind = data.get("kind")
        if kind == "it":
            serial = (data.get("serial_number") or "").strip()
            data["serial_number"] = serial
            if not serial:
                self.add_error("serial_number", "IT equipment needs a serial number.")
            elif ITAsset.objects.filter(serial_number=serial).exclude(pk=self.instance.pk).exists():
                self.add_error("serial_number", "Another asset already has this serial number.")
        if kind == "furniture":
            data["material"] = (data.get("material") or "").strip()
            if not data["material"]:
                self.add_error("material", "Furniture needs a material, e.g. wood or steel.")
        if self.editing and data.get("version") is None:
            data["version"] = self.instance.version
        return data
