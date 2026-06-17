import threading
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings

from .models import Configuration, Schedule, RunLog
from .forms import ConfigurationForm, ScheduleForm
from .runner import execute_run
from .scheduler import sync_schedule, remove_job


# ── Dashboard ────────────────────────────────────────────────────────────────

def dashboard(request):
    configs = Configuration.objects.all().order_by("name")
    recent_runs = RunLog.objects.select_related("configuration")[:10]
    schedules = Schedule.objects.select_related("configuration").all()
    snyk_token_set = bool(settings.SNYK_TOKEN)
    return render(request, "tickets/dashboard.html", {
        "configs": configs,
        "recent_runs": recent_runs,
        "schedules": schedules,
        "snyk_token_set": snyk_token_set,
    })


# ── Configurations ────────────────────────────────────────────────────────────

def config_list(request):
    configs = Configuration.objects.all().order_by("name")
    return render(request, "tickets/config_list.html", {"configs": configs})


def config_create(request):
    form = ConfigurationForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Configuration saved.")
        return redirect("config_list")
    return render(request, "tickets/config_form.html", {"form": form, "title": "New Configuration"})


def config_edit(request, pk):
    config = get_object_or_404(Configuration, pk=pk)
    form = ConfigurationForm(request.POST or None, instance=config)
    if form.is_valid():
        form.save()
        messages.success(request, "Configuration updated.")
        return redirect("config_list")
    return render(request, "tickets/config_form.html", {"form": form, "title": f"Edit: {config.name}"})


@require_POST
def config_delete(request, pk):
    config = get_object_or_404(Configuration, pk=pk)
    config.delete()
    messages.success(request, "Configuration deleted.")
    return redirect("config_list")


# ── Manual Run ────────────────────────────────────────────────────────────────

@require_POST
def run_now(request, pk):
    config = get_object_or_404(Configuration, pk=pk)
    if not settings.SNYK_TOKEN:
        messages.error(request, "SNYK_TOKEN is not set in your .env file.")
        return redirect("dashboard")

    run_log = RunLog.objects.create(configuration=config, triggered_by="manual")

    def _run():
        execute_run(run_log)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    messages.info(request, f"Run #{run_log.pk} started for '{config.name}'.")
    return redirect("run_detail", pk=run_log.pk)


# ── Run Logs ──────────────────────────────────────────────────────────────────

def run_list(request):
    runs = RunLog.objects.select_related("configuration", "schedule").all()
    return render(request, "tickets/run_list.html", {"runs": runs})


def run_detail(request, pk):
    run = get_object_or_404(RunLog, pk=pk)
    return render(request, "tickets/run_detail.html", {"run": run})


def run_status_api(request, pk):
    run = get_object_or_404(RunLog, pk=pk)
    return JsonResponse({
        "status": run.status,
        "output": run.output,
        "exit_code": run.exit_code,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    })


# ── Schedules ─────────────────────────────────────────────────────────────────

def schedule_list(request):
    schedules = Schedule.objects.select_related("configuration").all()
    return render(request, "tickets/schedule_list.html", {"schedules": schedules})


def schedule_create(request):
    form = ScheduleForm(request.POST or None)
    if form.is_valid():
        schedule = form.save()
        sync_schedule(schedule)
        messages.success(request, "Schedule created and activated.")
        return redirect("schedule_list")
    return render(request, "tickets/schedule_form.html", {"form": form, "title": "New Schedule"})


def schedule_edit(request, pk):
    schedule = get_object_or_404(Schedule, pk=pk)
    form = ScheduleForm(request.POST or None, instance=schedule)
    if form.is_valid():
        schedule = form.save()
        sync_schedule(schedule)
        messages.success(request, "Schedule updated.")
        return redirect("schedule_list")
    return render(request, "tickets/schedule_form.html", {"form": form, "title": "Edit Schedule"})


@require_POST
def schedule_delete(request, pk):
    schedule = get_object_or_404(Schedule, pk=pk)
    remove_job(schedule.job_id)
    schedule.delete()
    messages.success(request, "Schedule deleted.")
    return redirect("schedule_list")


@require_POST
def schedule_toggle(request, pk):
    schedule = get_object_or_404(Schedule, pk=pk)
    schedule.enabled = not schedule.enabled
    schedule.save()
    sync_schedule(schedule)
    state = "enabled" if schedule.enabled else "disabled"
    messages.success(request, f"Schedule {state}.")
    return redirect("schedule_list")
