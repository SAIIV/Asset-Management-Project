from django.contrib import admin

from .models import AIRecord, ModelVersion

admin.site.register([ModelVersion, AIRecord])
