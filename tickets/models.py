def build_config_dict(config, snyk_token):
    """Return the dict of settings to serialise into the temp config file."""
    cfg = {
        "orgID": config["org_id"],
        "token": snyk_token,
        "jiraProjectKey": config["jira_project_key"],
        "severity": config["severity"],
        "type": config["issue_type"],
        "jiraTicketType": config.get("jira_ticket_type") or "Bug",
        "priorityIsSeverity": bool(config.get("priority_is_severity")),
        "ifUpgradeAvailableOnly": bool(config.get("if_upgrade_available_only")),
        "dryRun": bool(config.get("dry_run")),
        "debug": bool(config.get("debug")),
    }
    for key, field in [
        ("projectID", "project_id"),
        ("api", "api_endpoint"),
        ("jiraProjectID", "jira_project_id"),
        ("assigneeId", "assignee_id"),
        ("assigneeName", "assignee_name"),
        ("maturityFilter", "maturity_filter"),
        ("labels", "labels"),
    ]:
        if config.get(field):
            cfg[key] = config[field]
    if config.get("priority_score_threshold") is not None:
        cfg["priorityScoreThreshold"] = config["priority_score_threshold"]
    return cfg
