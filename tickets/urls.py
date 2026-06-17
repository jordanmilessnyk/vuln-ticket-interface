from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    # Configurations
    path("configs/", views.config_list, name="config_list"),
    path("configs/new/", views.config_create, name="config_create"),
    path("configs/<int:pk>/edit/", views.config_edit, name="config_edit"),
    path("configs/<int:pk>/delete/", views.config_delete, name="config_delete"),
    path("configs/<int:pk>/run/", views.run_now, name="run_now"),

    # Schedules
    path("schedules/", views.schedule_list, name="schedule_list"),
    path("schedules/new/", views.schedule_create, name="schedule_create"),
    path("schedules/<int:pk>/edit/", views.schedule_edit, name="schedule_edit"),
    path("schedules/<int:pk>/delete/", views.schedule_delete, name="schedule_delete"),
    path("schedules/<int:pk>/toggle/", views.schedule_toggle, name="schedule_toggle"),

    # Run logs
    path("runs/", views.run_list, name="run_list"),
    path("runs/<int:pk>/", views.run_detail, name="run_detail"),
    path("runs/<int:pk>/status/", views.run_status_api, name="run_status_api"),
]
