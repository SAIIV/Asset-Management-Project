from django.contrib import admin

from .models import MatchRecommendation, RequestSpecification, ResourceRequest

admin.site.register([ResourceRequest, RequestSpecification, MatchRecommendation])
