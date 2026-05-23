"""Predefined audit event type constants and helper factory functions."""

from typing import Optional

# Event type constants
CONFIG_LOADED = "config.loaded"
CONFIG_RELOADED = "config.reloaded"
JOB_ADDED = "job.added"
JOB_REMOVED = "job.removed"
ALERT_SENT = "alert.sent"
ALERT_SUPPRESSED = "alert.suppressed"
DIGEST_SENT = "digest.sent"
RETENTION_PRUNED = "retention.pruned"
WATCHER_STARTED = "watcher.started"
WATCHER_STOPPED = "watcher.stopped"


def _make_event(event_type: str, actor: str, description: str) -> dict:
    return {"event_type": event_type, "actor": actor, "description": description}


def config_loaded(path: str, actor: str = "system") -> dict:
    return _make_event(CONFIG_LOADED, actor, f"Configuration loaded from '{path}'")


def config_reloaded(path: str, actor: str = "system") -> dict:
    return _make_event(CONFIG_RELOADED, actor, f"Configuration reloaded from '{path}'")


def job_added(job_name: str, actor: str = "system") -> dict:
    return _make_event(JOB_ADDED, actor, f"Job '{job_name}' added to watch list")


def job_removed(job_name: str, actor: str = "system") -> dict:
    return _make_event(JOB_REMOVED, actor, f"Job '{job_name}' removed from watch list")


def alert_sent(job_name: str, reason: str, actor: str = "system") -> dict:
    return _make_event(ALERT_SENT, actor, f"Alert sent for job '{job_name}': {reason}")


def alert_suppressed(job_name: str, reason: str, actor: str = "system") -> dict:
    return _make_event(ALERT_SUPPRESSED, actor, f"Alert suppressed for job '{job_name}': {reason}")


def digest_sent(recipient: str, actor: str = "system") -> dict:
    return _make_event(DIGEST_SENT, actor, f"Digest report sent to '{recipient}'")


def retention_pruned(rows_deleted: int, actor: str = "system") -> dict:
    return _make_event(RETENTION_PRUNED, actor, f"Retention policy pruned {rows_deleted} run record(s)")


def watcher_started(actor: str = "system") -> dict:
    return _make_event(WATCHER_STARTED, actor, "CronWatcher daemon started")


def watcher_stopped(actor: str = "system") -> dict:
    return _make_event(WATCHER_STOPPED, actor, "CronWatcher daemon stopped")
