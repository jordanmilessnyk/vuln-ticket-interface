"""
Flat-file data layer. All state lives under data/ as JSON.

  data/configs.json     — list of configuration dicts
  data/schedules.json   — list of schedule dicts
  data/runs/<id>.json   — one file per run (capped at MAX_RUNS)
"""

import json
import os
import uuid
import threading
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CONFIGS_FILE = DATA_DIR / "configs.json"
SCHEDULES_FILE = DATA_DIR / "schedules.json"
RUNS_DIR = DATA_DIR / "runs"
MAX_RUNS = 100

_lock = threading.Lock()


def _ensure_dirs():
    DATA_DIR.mkdir(exist_ok=True)
    RUNS_DIR.mkdir(exist_ok=True)


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(s):
    if not s:
        return None
    return datetime.fromisoformat(s)


# ── Generic helpers ───────────────────────────────────────────────────────────

def _read_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write_json(path, data):
    _ensure_dirs()
    tmp = str(path) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)  # atomic on POSIX


# ── Configs ───────────────────────────────────────────────────────────────────

def _load_configs():
    return _read_json(CONFIGS_FILE, [])


def _save_configs(configs):
    _write_json(CONFIGS_FILE, configs)


def list_configs():
    with _lock:
        configs = _load_configs()
    for c in configs:
        c["created_at"] = _parse_dt(c.get("created_at"))
        c["updated_at"] = _parse_dt(c.get("updated_at"))
    return sorted(configs, key=lambda c: c.get("name", ""))


def get_config(config_id):
    with _lock:
        configs = _load_configs()
    for c in configs:
        if c["id"] == config_id:
            c["created_at"] = _parse_dt(c.get("created_at"))
            c["updated_at"] = _parse_dt(c.get("updated_at"))
            return c
    return None


def create_config(data):
    now = _now_iso()
    config = {**data, "id": str(uuid.uuid4()), "created_at": now, "updated_at": now}
    with _lock:
        configs = _load_configs()
        configs.append(config)
        _save_configs(configs)
    return config


def update_config(config_id, data):
    with _lock:
        configs = _load_configs()
        for i, c in enumerate(configs):
            if c["id"] == config_id:
                configs[i] = {**c, **data, "id": config_id, "updated_at": _now_iso()}
                _save_configs(configs)
                return configs[i]
    return None


def delete_config(config_id):
    with _lock:
        configs = _load_configs()
        configs = [c for c in configs if c["id"] != config_id]
        _save_configs(configs)
    # Also remove any schedules for this config
    delete_schedules_for_config(config_id)


# ── Schedules ─────────────────────────────────────────────────────────────────

def _load_schedules():
    return _read_json(SCHEDULES_FILE, [])


def _save_schedules(schedules):
    _write_json(SCHEDULES_FILE, schedules)


def _enrich_schedule(s):
    s["created_at"] = _parse_dt(s.get("created_at"))
    config = get_config(s.get("config_id", ""))
    s["config_name"] = config["name"] if config else "(deleted)"
    s["config_description"] = config.get("description", "") if config else ""
    return s


def list_schedules():
    with _lock:
        schedules = _load_schedules()
    return [_enrich_schedule(s) for s in schedules]


def get_schedule(schedule_id):
    with _lock:
        schedules = _load_schedules()
    for s in schedules:
        if s["id"] == schedule_id:
            return _enrich_schedule(s)
    return None


def create_schedule(data):
    schedule = {**data, "id": str(uuid.uuid4()), "created_at": _now_iso()}
    with _lock:
        schedules = _load_schedules()
        schedules.append(schedule)
        _save_schedules(schedules)
    return _enrich_schedule(schedule)


def update_schedule(schedule_id, data):
    with _lock:
        schedules = _load_schedules()
        for i, s in enumerate(schedules):
            if s["id"] == schedule_id:
                schedules[i] = {**s, **data, "id": schedule_id}
                _save_schedules(schedules)
                return _enrich_schedule(schedules[i])
    return None


def delete_schedule(schedule_id):
    with _lock:
        schedules = _load_schedules()
        schedules = [s for s in schedules if s["id"] != schedule_id]
        _save_schedules(schedules)


def delete_schedules_for_config(config_id):
    with _lock:
        schedules = _load_schedules()
        schedules = [s for s in schedules if s.get("config_id") != config_id]
        _save_schedules(schedules)


def list_active_schedules():
    with _lock:
        schedules = _load_schedules()
    return [s for s in schedules if s.get("enabled", True)]


# ── Runs ──────────────────────────────────────────────────────────────────────

def _run_path(run_id):
    return RUNS_DIR / f"{run_id}.json"


def _enrich_run(r):
    r["started_at"] = _parse_dt(r.get("started_at"))
    r["finished_at"] = _parse_dt(r.get("finished_at"))
    if r["started_at"] and r["finished_at"]:
        r["duration_seconds"] = (r["finished_at"] - r["started_at"]).total_seconds()
    else:
        r["duration_seconds"] = None
    config = get_config(r.get("config_id", "")) if r.get("config_id") else None
    r["config_name"] = config["name"] if config else "(deleted)"
    r["configuration"] = config
    return r


def list_runs(limit=100):
    _ensure_dirs()
    runs = []
    for f in RUNS_DIR.glob("*.json"):
        try:
            with open(f) as fh:
                runs.append(json.load(fh))
        except (json.JSONDecodeError, OSError):
            continue
    runs.sort(key=lambda r: r.get("started_at", ""), reverse=True)
    return [_enrich_run(r) for r in runs[:limit]]


def get_run(run_id):
    try:
        with open(_run_path(run_id)) as f:
            r = json.load(f)
        return _enrich_run(r)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def create_run(config_id, triggered_by="manual", schedule_id=None):
    _ensure_dirs()
    run = {
        "id": str(uuid.uuid4()),
        "config_id": config_id,
        "schedule_id": schedule_id,
        "triggered_by": triggered_by,
        "status": "pending",
        "output": "",
        "exit_code": None,
        "started_at": _now_iso(),
        "finished_at": None,
    }
    with open(_run_path(run["id"]), "w") as f:
        json.dump(run, f, indent=2)
    _prune_old_runs()
    return run


def update_run(run_id, **fields):
    path = _run_path(run_id)
    with _lock:
        try:
            with open(path) as f:
                run = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None
        run.update(fields)
        tmp = str(path) + ".tmp"
        with open(tmp, "w") as f:
            json.dump(run, f, indent=2)
        os.replace(tmp, path)
    return run


def _prune_old_runs():
    files = sorted(RUNS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in files[MAX_RUNS:]:
        try:
            old.unlink()
        except OSError:
            pass
