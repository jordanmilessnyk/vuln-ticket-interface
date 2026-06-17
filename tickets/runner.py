import json
import os
import subprocess
import tempfile
from django.utils import timezone
from django.conf import settings

# Fixed, hardcoded command — no user data in the argument list.
_BASE_CMD = ["npx", "snyk-jira-tickets-for-new-vulns"]


def execute_run(run_log):
    from .models import RunLog
    config = run_log.configuration
    token = settings.SNYK_TOKEN
    config_dict = config.build_config_dict(token)

    run_log.status = RunLog.STATUS_RUNNING
    run_log.save(update_fields=["status"])

    # Write all configuration into a temp JSON file so that no DB-sourced
    # values appear as subprocess arguments (eliminates command injection risk).
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            prefix="snyk_jira_cfg_",
        ) as tmp:
            json.dump(config_dict, tmp)
            tmp_path = tmp.name

        # Only controlled, hardcoded strings go into the argument list.
        cmd = _BASE_CMD + ["--configFile", tmp_path]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            shell=False,
        )
        combined = result.stdout
        if result.stderr:
            combined += "\n--- STDERR ---\n" + result.stderr
        run_log.output = combined
        run_log.exit_code = result.returncode
        run_log.status = RunLog.STATUS_SUCCESS if result.returncode == 0 else RunLog.STATUS_FAILED
    except subprocess.TimeoutExpired:
        run_log.output = "Run timed out after 300 seconds."
        run_log.status = RunLog.STATUS_FAILED
        run_log.exit_code = -1
    except Exception as exc:
        run_log.output = f"Unexpected error: {exc}"
        run_log.status = RunLog.STATUS_FAILED
        run_log.exit_code = -1
    finally:
        if tmp is not None and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        run_log.finished_at = timezone.now()
        run_log.save(update_fields=["status", "output", "exit_code", "finished_at"])

    return run_log


def run_scheduled(configuration_id, schedule_id=None):
    from .models import Configuration, RunLog
    config = Configuration.objects.get(pk=configuration_id)
    schedule_kwargs = {}
    if schedule_id:
        from .models import Schedule
        schedule_kwargs["schedule"] = Schedule.objects.get(pk=schedule_id)

    run_log = RunLog.objects.create(
        configuration=config,
        triggered_by="schedule",
        **schedule_kwargs,
    )
    execute_run(run_log)
