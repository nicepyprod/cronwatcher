"""Tests for AuditLog persistence and querying."""

import time

import pytest

from cronwatcher.audit_log import AuditEntry, AuditLog
from cronwatcher.audit_events import (
    alert_sent,
    config_loaded,
    job_added,
    watcher_started,
)


@pytest.fixture
def log() -> AuditLog:
    return AuditLog(db_path=":memory:")


def test_record_returns_incrementing_ids(log: AuditLog) -> None:
    id1 = log.record(**config_loaded("/etc/cron.yaml"))
    id2 = log.record(**watcher_started())
    assert id2 > id1


def test_recent_returns_entries_newest_first(log: AuditLog) -> None:
    t0 = time.time()
    log.record(**config_loaded("/etc/cron.yaml"), timestamp=t0)
    log.record(**watcher_started(), timestamp=t0 + 1)
    entries = log.recent(limit=10)
    assert len(entries) == 2
    assert entries[0].timestamp >= entries[1].timestamp


def test_recent_respects_limit(log: AuditLog) -> None:
    for i in range(10):
        log.record(**job_added(f"job_{i}"))
    entries = log.recent(limit=3)
    assert len(entries) == 3


def test_by_event_type_filters_correctly(log: AuditLog) -> None:
    log.record(**config_loaded("/etc/cron.yaml"))
    log.record(**alert_sent("backup", "missed run"))
    log.record(**alert_sent("cleanup", "exit code 1"))
    log.record(**watcher_started())

    alerts = log.by_event_type("alert.sent")
    assert len(alerts) == 2
    assert all(e.event_type == "alert.sent" for e in alerts)


def test_as_dict_contains_expected_keys(log: AuditLog) -> None:
    log.record(**watcher_started())
    entry = log.recent(limit=1)[0]
    d = entry.as_dict()
    assert set(d.keys()) == {"id", "event_type", "actor", "description", "timestamp"}


def test_prune_before_removes_old_entries(log: AuditLog) -> None:
    now = time.time()
    log.record(**config_loaded("/etc/cron.yaml"), timestamp=now - 200)
    log.record(**watcher_started(), timestamp=now - 100)
    log.record(**alert_sent("job", "missed"), timestamp=now)

    deleted = log.prune_before(now - 50)
    assert deleted == 2
    remaining = log.recent(limit=10)
    assert len(remaining) == 1


def test_empty_log_returns_empty_list(log: AuditLog) -> None:
    assert log.recent() == []
    assert log.by_event_type("alert.sent") == []


def test_actor_and_description_stored_correctly(log: AuditLog) -> None:
    log.record(event_type="alert.sent", actor="watcher", description="test desc")
    entry = log.recent(limit=1)[0]
    assert entry.actor == "watcher"
    assert entry.description == "test desc"
