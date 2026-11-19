from django.urls import path

from . import views

app_name = "exchange"

urlpatterns = [
    path("catalogue/", views.catalogue_list, name="catalogue"),
    path("catalogue/<int:pk>/", views.catalogue_detail, name="catalogue_detail"),
    path("catalogue/<int:pk>/publish/", views.publish, name="publish"),
    path("catalogue/<int:pk>/unpublish/", views.unpublish, name="unpublish"),
    path("requests/", views.request_list, name="requests"),
    path("requests/new/", views.request_create, name="request_create"),
    path("requests/<int:pk>/", views.request_detail, name="request_detail"),
    path("requests/<int:pk>/edit/", views.request_edit, name="request_edit"),
    path("requests/<int:pk>/submit/", views.request_submit, name="request_submit"),
    path("requests/<int:pk>/cancel/", views.request_cancel, name="request_cancel"),

]
