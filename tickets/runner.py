import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone

from django.conf import settings
from . import store
from .models import build_config_dict

_BASE_CMD = ["npx", "snyk-jira-tickets-for-new-vulns"]


def execute_run(run_id):
    run = store.get_run(run_id)
    if not run:
        return

    config = store.get_config(run["config_id"])
    if not config:
        store.update_run(run_id, status="failed", output="Configuration not found.", exit_code=-1,
                         finished_at=datetime.now(timezone.utc).isoformat())
        return

    store.update_run(run_id, status="running")

    token = settings.SNYK_TOKEN
    config_dict = build_config_dict(config, token)

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, prefix="snyk_jira_cfg_"
        ) as tmp:
            json.dump(config_dict, tmp)
            tmp_path = tmp.name

        cmd = _BASE_CMD + ["--configFile", tmp_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, shell=False)

        combined = result.stdout
        if result.stderr:
            combined += "\n--- STDERR ---\n" + result.stderr

        store.update_run(
            run_id,
            status="success" if result.returncode == 0 else "failed",
            output=combined,
            exit_code=result.returncode,
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
    except subprocess.TimeoutExpired:
        store.update_run(run_id, status="failed", output="Run timed out after 300 seconds.",
                         exit_code=-1, finished_at=datetime.now(timezone.utc).isoformat())
    except Exception as exc:
        store.update_run(run_id, status="failed", output=f"Unexpected error: {exc}",
                         exit_code=-1, finished_at=datetime.now(timezone.utc).isoformat())
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def run_scheduled(config_id, schedule_id=None):
    run = store.create_run(config_id=config_id, triggered_by="schedule", schedule_id=schedule_id)
    execute_run(run["id"])
