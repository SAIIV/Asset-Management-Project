from django.urls import path

from . import maintenance_views as views

app_name = "maintenance"

urlpatterns = [
    path("", views.maintenance_list, name="list"),
    path("report/", views.report_fault, name="report"),
    path("faults/<int:pk>/start/", views.start_repair, name="start"),
    path("faults/<int:pk>/finish/", views.finish_repair, name="finish"),
    path("faults/<int:pk>/close/", views.close_fault, name="close"),
    path("assets/<int:pk>/propose/", views.propose, name="propose"),
    path("proposals/<int:pk>/decide/", views.decide, name="decide"),
    path("proposals/<int:pk>/execute/", views.execute, name="execute"),
    path("proposals/<int:pk>/cancel/", views.cancel_proposal, name="cancel"),
]
