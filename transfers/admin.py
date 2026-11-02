from django.contrib import admin

from .models import Approval, Reservation, Transfer

admin.site.register([Reservation, Approval, Transfer])
