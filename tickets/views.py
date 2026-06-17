import threading
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST
from django.conf import settings

from . import store
from .forms import ConfigurationForm, ScheduleForm
from .runner import execute_run
from .scheduler import sync_schedule, remove_job


def _get_config_or_404(config_id):
    config = store.get_config(config_id)
    if not config:
        raise Http404
    return config


def _get_schedule_or_404(schedule_id):
    schedule = store.get_schedule(schedule_id)
    if not schedule:
        raise Http404
    return schedule


def _get_run_or_404(run_id):
    run = store.get_run(run_id)
    if not run:
        raise Http404
    return run


# ── Dashboard ─────────────────────────────────────────────────────────────────

def dashboard(request):
    return render(request, "tickets/dashboard.html", {
        "configs": store.list_configs(),
        "recent_runs": store.list_runs(limit=10),
        "schedules": store.list_schedules(),
        "snyk_token_set": bool(settings.SNYK_TOKEN),
    })


# ── Configurations ────────────────────────────────────────────────────────────

def config_list(request):
    return render(request, "tickets/config_list.html", {"configs": store.list_configs()})


def config_create(request):
    form = ConfigurationForm(request.POST or None)
    if form.is_valid():
        store.create_config(form.cleaned_data)
        messages.success(request, "Configuration saved.")
        return redirect("config_list")
    return render(request, "tickets/config_form.html", {"form": form, "title": "New Configuration"})


def config_edit(request, pk):
    config = _get_config_or_404(pk)
    initial = {k: v for k, v in config.items() if k not in ("id", "created_at", "updated_at")}
    form = ConfigurationForm(request.POST or None, initial=initial)
    if form.is_valid():
        store.update_config(pk, form.cleaned_data)
        messages.success(request, "Configuration updated.")
        return redirect("config_list")
    return render(request, "tickets/config_form.html", {"form": form, "title": f"Edit: {config['name']}"})


@require_POST
def config_delete(request, pk):
    _get_config_or_404(pk)
    store.delete_config(pk)
    messages.success(request, "Configuration deleted.")
    return redirect("config_list")


# ── Manual Run ────────────────────────────────────────────────────────────────

@require_POST
def run_now(request, pk):
    config = _get_config_or_404(pk)
    if not settings.SNYK_TOKEN:
        messages.error(request, "SNYK_TOKEN is not set in your .env file.")
        return redirect("dashboard")

    run = store.create_run(config_id=pk, triggered_by="manual")
    thread = threading.Thread(target=execute_run, args=(run["id"],), daemon=True)
    thread.start()

    messages.info(request, f"Run started for '{config['name']}'.")
    return redirect("run_detail", pk=run["id"])


# ── Run Logs ──────────────────────────────────────────────────────────────────

def run_list(request):
    return render(request, "tickets/run_list.html", {"runs": store.list_runs()})


def run_detail(request, pk):
    run = _get_run_or_404(pk)
    return render(request, "tickets/run_detail.html", {"run": run})


def run_status_api(request, pk):
    run = _get_run_or_404(pk)
    return JsonResponse({
        "status": run["status"],
        "output": run["output"],
        "exit_code": run["exit_code"],
        "finished_at": run["finished_at"].isoformat() if run["finished_at"] else None,
    })


# ── Schedules ─────────────────────────────────────────────────────────────────

def schedule_list(request):
    return render(request, "tickets/schedule_list.html", {"schedules": store.list_schedules()})


def schedule_create(request):
    configs = store.list_configs()
    form = ScheduleForm(request.POST or None, configs=configs)
    if form.is_valid():
        schedule = store.create_schedule(form.cleaned_data)
        sync_schedule(schedule)
        messages.success(request, "Schedule created and activated.")
        return redirect("schedule_list")
    return render(request, "tickets/schedule_form.html", {"form": form, "title": "New Schedule"})


def schedule_edit(request, pk):
    schedule = _get_schedule_or_404(pk)
    configs = store.list_configs()
    initial = {"config_id": schedule["config_id"],
               "cron_expression": schedule["cron_expression"],
               "enabled": schedule.get("enabled", True)}
    form = ScheduleForm(request.POST or None, configs=configs, initial=initial)
    if form.is_valid():
        schedule = store.update_schedule(pk, form.cleaned_data)
        sync_schedule(schedule)
        messages.success(request, "Schedule updated.")
        return redirect("schedule_list")
    return render(request, "tickets/schedule_form.html", {"form": form, "title": "Edit Schedule"})


@require_POST
def schedule_delete(request, pk):
    schedule = _get_schedule_or_404(pk)
    remove_job(f"schedule_{pk}")
    store.delete_schedule(pk)
    messages.success(request, "Schedule deleted.")
    return redirect("schedule_list")


@require_POST
def schedule_toggle(request, pk):
    schedule = _get_schedule_or_404(pk)
    updated = store.update_schedule(pk, {"enabled": not schedule.get("enabled", True)})
    sync_schedule(updated)
    state = "enabled" if updated["enabled"] else "disabled"
    messages.success(request, f"Schedule {state}.")
    return redirect("schedule_list")
