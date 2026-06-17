import re
from django import forms

_SAFE_ID = re.compile(r'^[\w\-\.]+$')
_SAFE_KEY = re.compile(r'^[A-Z0-9_\-]+$', re.I)
_SAFE_LIST = re.compile(r'^[\w\-]+(,[\w\-]+)*$')
_SAFE_URL = re.compile(r'^https?://[\w\-\./:]+$')

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
MATURITY_ALLOWED = {"no-data", "no-known-exploit", "proof-of-concept", "functional", "mature"}


class ConfigurationForm(forms.Form):
    name = forms.CharField(max_length=100, label="Profile Name")
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))

    org_id = forms.CharField(max_length=200, label="Snyk Org ID")
    project_id = forms.CharField(max_length=200, required=False, label="Snyk Project ID")
    api_endpoint = forms.CharField(
        max_length=500, required=False, label="API Endpoint",
        widget=forms.TextInput(attrs={"placeholder": "Leave blank for default Snyk API"}),
    )

    jira_project_key = forms.CharField(max_length=50, label="Jira Project Key")
    jira_project_id = forms.CharField(max_length=50, required=False, label="Jira Project ID")
    jira_ticket_type = forms.CharField(max_length=50, required=False, initial="Bug", label="Jira Ticket Type")
    assignee_id = forms.CharField(max_length=200, required=False, label="Assignee ID")
    assignee_name = forms.CharField(max_length=200, required=False, label="Assignee Name")
    labels = forms.CharField(
        max_length=500, required=False, label="Labels (comma-separated)",
        widget=forms.TextInput(attrs={"placeholder": "e.g. snyk,security"}),
    )

    severity = forms.ChoiceField(choices=SEVERITY_CHOICES, initial="low", label="Min Severity")
    issue_type = forms.ChoiceField(choices=ISSUE_TYPE_CHOICES, initial="all", label="Issue Type")
    maturity_filter = forms.CharField(
        max_length=200, required=False, label="Maturity Filter",
        widget=forms.TextInput(attrs={"placeholder": "e.g. mature,functional"}),
    )
    priority_score_threshold = forms.IntegerField(required=False, label="Priority Score Threshold (0–1000)")

    priority_is_severity = forms.BooleanField(required=False, label="Priority = Severity")
    if_upgrade_available_only = forms.BooleanField(required=False, label="Upgradable issues only")
    dry_run = forms.BooleanField(required=False, label="Dry run")
    debug = forms.BooleanField(required=False, label="Debug logging")

    def clean_org_id(self):
        v = self.cleaned_data.get("org_id", "")
        if not _SAFE_ID.match(v):
            raise forms.ValidationError("Org ID may only contain letters, digits, hyphens, underscores, and dots.")
        return v

    def clean_project_id(self):
        v = self.cleaned_data.get("project_id", "")
        if v and not _SAFE_ID.match(v):
            raise forms.ValidationError("Project ID may only contain letters, digits, hyphens, underscores, and dots.")
        return v

    def clean_jira_project_key(self):
        v = self.cleaned_data.get("jira_project_key", "")
        if not _SAFE_KEY.match(v):
            raise forms.ValidationError("Jira Project Key may only contain letters, digits, hyphens, and underscores.")
        return v

    def clean_jira_project_id(self):
        v = self.cleaned_data.get("jira_project_id", "")
        if v and not _SAFE_ID.match(v):
            raise forms.ValidationError("Jira Project ID may only contain letters, digits, hyphens, underscores, and dots.")
        return v

    def clean_jira_ticket_type(self):
        v = self.cleaned_data.get("jira_ticket_type", "")
        if v and not _SAFE_ID.match(v):
            raise forms.ValidationError("Ticket type may only contain letters, digits, hyphens, underscores, and dots.")
        return v

    def clean_assignee_id(self):
        v = self.cleaned_data.get("assignee_id", "")
        if v and not _SAFE_ID.match(v):
            raise forms.ValidationError("Assignee ID may only contain letters, digits, hyphens, underscores, and dots.")
        return v

    def clean_assignee_name(self):
        v = self.cleaned_data.get("assignee_name", "")
        if v and not re.match(r'^[\w\-\. @]+$', v):
            raise forms.ValidationError("Assignee Name contains invalid characters.")
        return v

    def clean_labels(self):
        v = self.cleaned_data.get("labels", "")
        if v and not _SAFE_LIST.match(v):
            raise forms.ValidationError("Labels must be comma-separated alphanumeric values.")
        return v

    def clean_maturity_filter(self):
        v = self.cleaned_data.get("maturity_filter", "")
        if v:
            bad = [p.strip() for p in v.split(",") if p.strip() not in MATURITY_ALLOWED]
            if bad:
                raise forms.ValidationError(
                    f"Unknown maturity values: {', '.join(bad)}. "
                    "Allowed: no-data, no-known-exploit, proof-of-concept, functional, mature."
                )
        return v

    def clean_api_endpoint(self):
        v = self.cleaned_data.get("api_endpoint", "")
        if v and not _SAFE_URL.match(v):
            raise forms.ValidationError("API Endpoint must be a valid https:// or http:// URL.")
        return v

    def clean_priority_score_threshold(self):
        v = self.cleaned_data.get("priority_score_threshold")
        if v is not None and not (0 <= v <= 1000):
            raise forms.ValidationError("Priority score threshold must be between 0 and 1000.")
        return v


class ScheduleForm(forms.Form):
    config_id = forms.ChoiceField(label="Configuration")
    cron_expression = forms.CharField(
        max_length=100, label="Cron Expression",
        widget=forms.TextInput(attrs={"placeholder": "e.g. 0 9 * * 1"}),
        help_text="5-part cron: minute hour day month weekday (UTC).",
    )
    enabled = forms.BooleanField(required=False, initial=True, label="Enable immediately after saving")

    def __init__(self, *args, configs=None, **kwargs):
        super().__init__(*args, **kwargs)
        configs = configs or []
        self.fields["config_id"].choices = [(c["id"], c["name"]) for c in configs]

    def clean_cron_expression(self):
        expr = self.cleaned_data.get("cron_expression", "").strip()
        parts = expr.split()
        if len(parts) != 5:
            raise forms.ValidationError("Enter a valid 5-part cron expression (minute hour day month weekday).")
        if not all(re.match(r'^[\d\*\/\-,]+$', p) for p in parts):
            raise forms.ValidationError("Cron expression contains invalid characters.")
        return expr
