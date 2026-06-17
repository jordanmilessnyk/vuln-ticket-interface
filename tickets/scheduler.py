from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = BackgroundScheduler(timezone="UTC")


def start():
    scheduler.start()
    _sync_all_schedules()


def _sync_all_schedules():
    from . import store
    for schedule in store.list_active_schedules():
        _register_job(schedule)


def _register_job(schedule):
    parts = schedule["cron_expression"].split()
    trigger = CronTrigger(
        minute=parts[0], hour=parts[1], day=parts[2],
        month=parts[3], day_of_week=parts[4], timezone="UTC",
    )
    from .runner import run_scheduled
    scheduler.add_job(
        run_scheduled,
        trigger=trigger,
        id=f"schedule_{schedule['id']}",
        args=[schedule["config_id"], schedule["id"]],
        replace_existing=True,
        misfire_grace_time=3600,
    )


def sync_schedule(schedule):
    job_id = f"schedule_{schedule['id']}"
    if not schedule.get("enabled"):
        _remove_job(job_id)
        return
    _register_job(schedule)


def _remove_job(job_id):
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass


def remove_job(job_id):
    _remove_job(job_id)
