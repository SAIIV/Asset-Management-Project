from django.contrib import admin

from . import models


@admin.register(models.Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "category", "owner_department", "condition", "status", "is_listed"]
    list_filter = ["status", "condition", "category", "owner_department"]
    search_fields = ["name", "description"]
    exclude = ["embedding"]  # vectors are filled by the AI gateway, not by hand


for model in (models.Department, models.Category, models.ITAsset, models.LabEquipment, models.FurnitureAsset,
              models.AssetCollection, models.Inspection, models.MaintenanceRecord, models.LifecycleAction):
    admin.site.register(model)
