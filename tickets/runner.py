import os
import shutil
import subprocess
import tempfile
import yaml
from datetime import datetime, timezone

from django.conf import settings
from . import store


def _get_binary():
    return getattr(settings, "SNYK_JIRA_BINARY", "snyk-jira-sync")


def _build_jira_yaml(config):
    """Build the jira.yaml structure expected by the binary.

    The token is intentionally excluded — the tool does not support it in the
    config file and requires it to be passed as a CLI flag.
    """
    snyk_section = {
        "orgID": config["org_id"],
        "severity": config["severity"],
        "type": config["issue_type"],
        "ifUpgradeAvailableOnly": bool(config.get("if_upgrade_available_only")),
    }
    jira_section = {
        "jiraProjectKey": config["jira_project_key"],
        "jiraTicketType": config.get("jira_ticket_type") or "Bug",
        "priorityIsSeverity": bool(config.get("priority_is_severity")),
    }

    if config.get("project_id"):
        snyk_section["projectID"] = config["project_id"]
    if config.get("api_endpoint"):
        snyk_section["api"] = config["api_endpoint"]
    if config.get("maturity_filter"):
        snyk_section["maturityFilter"] = config["maturity_filter"]
    if config.get("priority_score_threshold") is not None:
        snyk_section["priorityScoreThreshold"] = config["priority_score_threshold"]
    if config.get("jira_project_id"):
        jira_section["jiraProjectID"] = config["jira_project_id"]
    if config.get("assignee_id"):
        jira_section["assigneeId"] = config["assignee_id"]
    if config.get("assignee_name"):
        jira_section["assigneeName"] = config["assignee_name"]
    if config.get("labels"):
        jira_section["labels"] = config["labels"]

    return {"schema": 1, "snyk": snyk_section, "jira": jira_section}


def execute_run(run_id):
    run = store.get_run(run_id)
    if not run:
        return

    config = store.get_config(run["config_id"])
    if not config:
        store.update_run(run_id, status="failed", output="Configuration not found.",
                         exit_code=-1, finished_at=datetime.now(timezone.utc).isoformat())
        return

    store.update_run(run_id, status="running")

    tmp_dir = None
    try:
        # Create a temp directory and write jira.yaml inside it.
        # The binary expects --configFile to point to a directory containing jira.yaml.
        tmp_dir = tempfile.mkdtemp(prefix="snyk_jira_")
        yaml_path = os.path.join(tmp_dir, "jira.yaml")
        with open(yaml_path, "w") as f:
            yaml.dump(_build_jira_yaml(config), f, default_flow_style=False)

        # Token comes from the environment (not the DB) so it is safe as a CLI arg.
        # dryRun and debug are hardcoded flag strings — no DB value is interpolated.
        token = settings.SNYK_TOKEN
        cmd = [_get_binary(), "--configFile", tmp_dir, f"--token={token}"]
        if config.get("dry_run"):
            cmd.append("--dryRun")
        if config.get("debug"):
            cmd.append("--debug")

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
        if tmp_dir and os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)


def run_scheduled(config_id, schedule_id=None):
    run = store.create_run(config_id=config_id, triggered_by="schedule", schedule_id=schedule_id)
    execute_run(run["id"])
