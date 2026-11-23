from django.urls import path

from . import views

app_name = "transfers"

urlpatterns = [
    path("", views.transfer_list, name="list"),
    path("incoming/", views.incoming, name="incoming"),
    path("requests/<int:pk>/", views.custodian_request, name="custodian_request"),
    path("requests/<int:pk>/cannot-supply/", views.cannot_supply, name="cannot_supply"),

    path("approvals/", views.approvals, name="approvals"),
    path("approvals/<int:pk>/", views.approval_detail, name="approval_detail"),
    path("<int:pk>/release/", views.release, name="release"),
    path("<int:pk>/receive/", views.receive, name="receive"),
    path("go/request/<int:pk>/", views.open_request, name="open_request"),
    path("go/transfer/<int:pk>/", views.open_transfer, name="open_transfer"),
]
