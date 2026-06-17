from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    path("configs/", views.config_list, name="config_list"),
    path("configs/new/", views.config_create, name="config_create"),
    path("configs/<str:pk>/edit/", views.config_edit, name="config_edit"),
    path("configs/<str:pk>/delete/", views.config_delete, name="config_delete"),
    path("configs/<str:pk>/run/", views.run_now, name="run_now"),

    path("schedules/", views.schedule_list, name="schedule_list"),
    path("schedules/new/", views.schedule_create, name="schedule_create"),
    path("schedules/<str:pk>/edit/", views.schedule_edit, name="schedule_edit"),
    path("schedules/<str:pk>/delete/", views.schedule_delete, name="schedule_delete"),
    path("schedules/<str:pk>/toggle/", views.schedule_toggle, name="schedule_toggle"),

    path("runs/", views.run_list, name="run_list"),
    path("runs/<str:pk>/", views.run_detail, name="run_detail"),
    path("runs/<str:pk>/status/", views.run_status_api, name="run_status_api"),
]
