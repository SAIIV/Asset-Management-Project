from django.urls import path

from . import views

app_name = "exchange"

urlpatterns = [
    path("catalogue/", views.catalogue_list, name="catalogue"),
    path("catalogue/<int:pk>/", views.catalogue_detail, name="catalogue_detail"),
    path("catalogue/<int:pk>/publish/", views.publish, name="publish"),
    path("catalogue/<int:pk>/unpublish/", views.unpublish, name="unpublish"),
]
