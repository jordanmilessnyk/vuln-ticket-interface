# Snyk Jira Ticket Interface

A Django web application for running and scheduling [snyk-jira-tickets-for-new-vulns](https://docs.snyk.io/developer-tools/snyk-apps/tool-jira-tickets-for-new-vulns) — the Snyk CLI tool that automatically opens Jira tickets for newly discovered vulnerabilities.

## Features

- **Configuration profiles** — create named profiles with all CLI flags configured via a UI form (Snyk org/project, Jira project, severity filters, assignees, labels, and more)
- **Manual runs** — trigger a run instantly from the dashboard with live output streaming
- **Cron scheduling** — attach cron expressions to any configuration for automated recurring runs
- **Run history** — full log of every run with status, exit code, duration, and output

## Prerequisites

- Python 3.9+
- Node.js + npx (used to invoke `snyk-jira-tickets-for-new-vulns`)
- A Snyk API token
- A Jira project to write tickets to

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/jordanmilessnyk/vuln-ticket-interface.git
cd vuln-ticket-interface

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Configure your environment
cp .env.example .env
# Edit .env and set:
#   SNYK_TOKEN=snyk_...
#   SECRET_KEY=<a long random string for production>

# 4. Apply database migrations
python manage.py migrate
```

## Running

```bash
RUN_MAIN=true python manage.py runserver
```

Open **http://localhost:8000** in your browser.

> `RUN_MAIN=true` is required to start the cron scheduler that fires scheduled runs.

## Usage

1. **Create a configuration** — click *+ New Configuration* and fill in your Snyk org ID, Jira project key, and any filters/options
2. **Run manually** — click *▶ Run* on any configuration from the Dashboard or Configurations page
3. **Schedule a run** — go to *Schedules → + New Schedule*, pick a configuration, and enter a cron expression

### Cron expression examples

| Expression | Meaning |
|---|---|
| `0 9 * * 1` | Every Monday at 09:00 UTC |
| `0 8 * * 1-5` | Weekdays at 08:00 UTC |
| `0 */6 * * *` | Every 6 hours |
| `0 0 * * *` | Daily at midnight UTC |

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `SNYK_TOKEN` | Yes | Snyk API token |
| `SECRET_KEY` | No | Django secret key (auto-generated default is fine for local use) |
| `DEBUG` | No | Set to `False` in production (default: `True`) |

## Project structure

```
├── config/          # Django project settings and URL config
├── tickets/         # Main app — models, views, forms, runner, scheduler
├── templates/       # HTML templates
├── requirements.txt
├── .env.example
└── manage.py
```

## Security notes

- `SNYK_TOKEN` is stored only in `.env` and never persisted to the database
- All configuration values are validated against strict allowlists before use
- Configuration is passed to the CLI tool via a temporary JSON file (not as shell arguments) to prevent argument injection
- `.env` is excluded from version control via `.gitignore`
