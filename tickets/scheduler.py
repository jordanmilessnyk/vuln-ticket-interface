from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore

scheduler = BackgroundScheduler(timezone="UTC")
scheduler.add_jobstore(DjangoJobStore(), "default")


def start():
    from .models import Schedule
    scheduler.start()
    _sync_all_schedules()


def _sync_all_schedules():
    from .models import Schedule
    for schedule in Schedule.objects.filter(enabled=True).select_related("configuration"):
        _register_job(schedule)


def _register_job(schedule):
    parts = schedule.cron_expression.split()
    trigger = CronTrigger(
        minute=parts[0],
        hour=parts[1],
        day=parts[2],
        month=parts[3],
        day_of_week=parts[4],
        timezone="UTC",
    )
    from .runner import run_scheduled
    scheduler.add_job(
        run_scheduled,
        trigger=trigger,
        id=schedule.job_id,
        args=[schedule.configuration_id, schedule.pk],
        replace_existing=True,
        misfire_grace_time=3600,
    )


def sync_schedule(schedule):
    if not schedule.enabled:
        remove_job(schedule.job_id)
        return
    _register_job(schedule)


def remove_job(job_id):
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass
