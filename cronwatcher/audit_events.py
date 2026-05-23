"""Factory functions for structured audit log events in cronwatcher."""

import time
from typing import Any

from cronwatcher.audit_log import AuditLog


def _make_event(event_type: str, details: dict[str, Any]) -> dict[str, Any]:
    return {"event_type": event_type, "timestamp": time.time(), **details}


def config_loaded(log: AuditLog, path: str) -> None:
    log.record(event_type="config_loaded", details={"path": path})


def config_reloaded(log: AuditLog, path: str) -> None:
    log.record(event_type="config_reloaded", details={"path": path})


def job_added(log: AuditLog, job_name: str) -> None:
    log.record(event_type="job_added", details={"job_name": job_name})


def job_removed(log: AuditLog, job_name: str) -> None:
    log.record(event_type="job_removed", details={"job_name": job_name})


def alert_sent(log: AuditLog, job_name: str, reason: str) -> None:
    log.record(event_type="alert_sent", details={"job_name": job_name, "reason": reason})


def alert_suppressed(log: AuditLog, job_name: str, reason: str) -> None:
    log.record(event_type="alert_suppressed", details={"job_name": job_name, "reason": reason})


def lock_acquired(log: AuditLog, job_name: str, owner: str) -> None:
    log.record(event_type="lock_acquired", details={"job_name": job_name, "owner": owner})


def lock_released(log: AuditLog, job_name: str, owner: str) -> None:
    log.record(event_type="lock_released", details={"job_name": job_name, "owner": owner})


def lock_rejected(log: AuditLog, job_name: str, held_by: str) -> None:
    log.record(event_type="lock_rejected", details={"job_name": job_name, "held_by": held_by})
