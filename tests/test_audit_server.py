"""Tests for the AuditServer HTTP endpoint."""

import json
import time
from urllib.request import urlopen
from urllib.error import HTTPError

import pytest

from cronwatcher.audit_log import AuditLog
from cronwatcher.audit_server import AuditServer
from cronwatcher.audit_events import alert_sent, watcher_started, config_loaded

PORT = 18084


@pytest.fixture(scope="module")
def server() -> AuditServer:  # type: ignore[misc]
    log = AuditLog(db_path=":memory:")
    now = time.time()
    log.record(**config_loaded("/etc/cron.yaml"), timestamp=now - 10)
    log.record(**alert_sent("backup", "missed run"), timestamp=now - 5)
    log.record(**alert_sent("cleanup", "exit 1"), timestamp=now - 1)
    log.record(**watcher_started(), timestamp=now)
    srv = AuditServer(log, host="127.0.0.1", port=PORT)
    srv.start()
    yield srv
    srv.stop()


def _get(path: str) -> object:
    with urlopen(f"http://127.0.0.1:{PORT}{path}") as resp:
        return json.loads(resp.read())


def test_audit_returns_all_entries(server: AuditServer) -> None:
    data = _get("/audit")
    assert isinstance(data, list)
    assert len(data) == 4


def test_audit_entries_have_expected_keys(server: AuditServer) -> None:
    data = _get("/audit")
    assert isinstance(data, list)
    entry = data[0]
    assert "event_type" in entry
    assert "actor" in entry
    assert "description" in entry
    assert "timestamp" in entry


def test_audit_filter_by_event_type(server: AuditServer) -> None:
    data = _get("/audit?event_type=alert.sent")
    assert isinstance(data, list)
    assert len(data) == 2
    assert all(e["event_type"] == "alert.sent" for e in data)


def test_audit_limit_param(server: AuditServer) -> None:
    data = _get("/audit?limit=2")
    assert isinstance(data, list)
    assert len(data) == 2


def test_unknown_path_returns_404(server: AuditServer) -> None:
    with pytest.raises(HTTPError) as exc_info:
        _get("/nonexistent")
    assert exc_info.value.code == 404
