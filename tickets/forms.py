import re
from django import forms
from .models import Configuration, Schedule

# Safe patterns for values that become CLI arguments
_SAFE_ID = re.compile(r'^[\w\-\.]+$')          # org IDs, project IDs, ticket types
_SAFE_KEY = re.compile(r'^[A-Z0-9_\-]+$', re.I) # Jira project key
_SAFE_LIST = re.compile(r'^[\w\-]+(,[\w\-]+)*$') # comma-separated labels/maturity
_SAFE_URL = re.compile(r'^https?://[\w\-\./:]+$') # API endpoint


def _require_safe_id(value, field_name):
    if value and not _SAFE_ID.match(value):
        raise forms.ValidationError(
            f"{field_name} may only contain letters, digits, hyphens, underscores, and dots."
        )
    return value


class ConfigurationForm(forms.ModelForm):
    class Meta:
        model = Configuration
        exclude = ["created_at", "updated_at"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
            "maturity_filter": forms.TextInput(attrs={"placeholder": "e.g. mature,functional"}),
            "labels": forms.TextInput(attrs={"placeholder": "e.g. snyk,security"}),
            "api_endpoint": forms.TextInput(attrs={"placeholder": "Leave blank for default Snyk API"}),
        }

    def clean_org_id(self):
        return _require_safe_id(self.cleaned_data.get("org_id", ""), "Snyk Org ID")

    def clean_project_id(self):
        return _require_safe_id(self.cleaned_data.get("project_id", ""), "Snyk Project ID")

    def clean_jira_project_key(self):
        value = self.cleaned_data.get("jira_project_key", "")
        if value and not _SAFE_KEY.match(value):
            raise forms.ValidationError(
                "Jira Project Key may only contain letters, digits, hyphens, and underscores."
            )
        return value

    def clean_jira_project_id(self):
        return _require_safe_id(self.cleaned_data.get("jira_project_id", ""), "Jira Project ID")

    def clean_jira_ticket_type(self):
        return _require_safe_id(self.cleaned_data.get("jira_ticket_type", ""), "Jira Ticket Type")

    def clean_assignee_id(self):
        return _require_safe_id(self.cleaned_data.get("assignee_id", ""), "Assignee ID")

    def clean_assignee_name(self):
        value = self.cleaned_data.get("assignee_name", "")
        if value and not re.match(r'^[\w\-\. @]+$', value):
            raise forms.ValidationError(
                "Assignee Name may only contain letters, digits, spaces, hyphens, dots, and @."
            )
        return value

    def clean_labels(self):
        value = self.cleaned_data.get("labels", "")
        if value and not _SAFE_LIST.match(value):
            raise forms.ValidationError(
                "Labels must be comma-separated alphanumeric values (e.g. snyk,security)."
            )
        return value

    def clean_maturity_filter(self):
        value = self.cleaned_data.get("maturity_filter", "")
        allowed = {"", "no-data", "no-known-exploit", "proof-of-concept", "functional", "mature"}
        if value:
            parts = [p.strip() for p in value.split(",")]
            bad = [p for p in parts if p not in allowed]
            if bad:
                raise forms.ValidationError(
                    f"Unknown maturity values: {', '.join(bad)}. "
                    "Allowed: no-data, no-known-exploit, proof-of-concept, functional, mature."
                )
        return value

    def clean_api_endpoint(self):
        value = self.cleaned_data.get("api_endpoint", "")
        if value and not _SAFE_URL.match(value):
            raise forms.ValidationError(
                "API Endpoint must be a valid https:// or http:// URL."
            )
        return value

    def clean_priority_score_threshold(self):
        value = self.cleaned_data.get("priority_score_threshold")
        if value is not None and not (0 <= value <= 1000):
            raise forms.ValidationError("Priority score threshold must be between 0 and 1000.")
        return value


class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = ["configuration", "cron_expression", "enabled"]
        widgets = {
            "cron_expression": forms.TextInput(attrs={"placeholder": "e.g. 0 9 * * 1"}),
        }

    def clean_cron_expression(self):
        expr = self.cleaned_data.get("cron_expression", "").strip()
        parts = expr.split()
        if len(parts) != 5:
            raise forms.ValidationError("Enter a valid 5-part cron expression (minute hour day month weekday).")
        # Each part may only contain digits, *, /, -, and comma
        if not all(re.match(r'^[\d\*\/\-,]+$', p) for p in parts):
            raise forms.ValidationError("Cron expression contains invalid characters.")
        return expr
