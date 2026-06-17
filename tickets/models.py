from django.db import models


class Configuration(models.Model):
    SEVERITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]
    ISSUE_TYPE_CHOICES = [
        ("all", "All"),
        ("vuln", "Vulnerabilities only"),
        ("license", "Licenses only"),
    ]

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    # Required fields
    org_id = models.CharField(max_length=200, verbose_name="Snyk Org ID")
    jira_project_key = models.CharField(max_length=50, verbose_name="Jira Project Key")

    # Optional Snyk fields
    project_id = models.CharField(max_length=200, blank=True, verbose_name="Snyk Project ID")
    api_endpoint = models.CharField(max_length=500, blank=True, verbose_name="API Endpoint")

    # Optional Jira fields
    jira_project_id = models.CharField(max_length=50, blank=True, verbose_name="Jira Project ID")
    jira_ticket_type = models.CharField(max_length=50, default="Bug", verbose_name="Jira Ticket Type")
    assignee_id = models.CharField(max_length=200, blank=True, verbose_name="Assignee ID")
    assignee_name = models.CharField(max_length=200, blank=True, verbose_name="Assignee Name")
    labels = models.CharField(max_length=500, blank=True, verbose_name="Labels (comma-separated)")

    # Filter fields
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default="low", verbose_name="Min Severity")
    issue_type = models.CharField(max_length=20, choices=ISSUE_TYPE_CHOICES, default="all", verbose_name="Issue Type")
    maturity_filter = models.CharField(max_length=200, blank=True, verbose_name="Maturity Filter")
    priority_score_threshold = models.IntegerField(null=True, blank=True, verbose_name="Priority Score Threshold (0–1000)")

    # Boolean flags
    priority_is_severity = models.BooleanField(default=False, verbose_name="Priority = Severity")
    if_upgrade_available_only = models.BooleanField(default=False, verbose_name="Upgradable issues only")
    dry_run = models.BooleanField(default=False, verbose_name="Dry run")
    debug = models.BooleanField(default=False, verbose_name="Debug logging")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def build_config_dict(self, snyk_token):
        """Return a plain dict of all settings for serialisation into a config file."""
        cfg = {
            "orgID": self.org_id,
            "token": snyk_token,
            "jiraProjectKey": self.jira_project_key,
            "severity": self.severity,
            "type": self.issue_type,
            "jiraTicketType": self.jira_ticket_type or "Bug",
            "priorityIsSeverity": self.priority_is_severity,
            "ifUpgradeAvailableOnly": self.if_upgrade_available_only,
            "dryRun": self.dry_run,
            "debug": self.debug,
        }
        if self.project_id:
            cfg["projectID"] = self.project_id
        if self.api_endpoint:
            cfg["api"] = self.api_endpoint
        if self.jira_project_id:
            cfg["jiraProjectID"] = self.jira_project_id
        if self.assignee_id:
            cfg["assigneeId"] = self.assignee_id
        if self.assignee_name:
            cfg["assigneeName"] = self.assignee_name
        if self.maturity_filter:
            cfg["maturityFilter"] = self.maturity_filter
        if self.priority_score_threshold is not None:
            cfg["priorityScoreThreshold"] = self.priority_score_threshold
        if self.labels:
            cfg["labels"] = self.labels
        return cfg


class Schedule(models.Model):
    configuration = models.ForeignKey(Configuration, on_delete=models.CASCADE, related_name="schedules")
    cron_expression = models.CharField(
        max_length=100,
        help_text="Standard 5-part cron: minute hour day month weekday. E.g. '0 9 * * 1' = every Monday at 9am UTC",
    )
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.configuration.name} — {self.cron_expression}"

    @property
    def job_id(self):
        return f"schedule_{self.pk}"


class RunLog(models.Model):
    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
    ]

    configuration = models.ForeignKey(Configuration, on_delete=models.SET_NULL, null=True, related_name="runs")
    schedule = models.ForeignKey(Schedule, on_delete=models.SET_NULL, null=True, blank=True, related_name="runs")
    triggered_by = models.CharField(max_length=50, default="manual")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    output = models.TextField(blank=True)
    exit_code = models.IntegerField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"Run {self.pk} — {self.configuration} — {self.status}"

    @property
    def duration_seconds(self):
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None
