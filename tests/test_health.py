"""Tests for cronwatcher.health and cronwatcher.health_server."""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.health import HealthChecker, HealthStatus
from cronwatcher.health_server import HealthServer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_store():
    store = MagicMock()
    store.recent_runs.return_value = [
        {"success": True},
        {"success": True},
        {"success": False},
    ]
    return store


@pytest.fixture()
def mock_log():
    log = MagicMock()
    entry = MagicMock()
    entry.sent_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    log.recent_entries.return_value = [entry]
    return log


@pytest.fixture()
def checker(mock_store, mock_log):
    return HealthChecker(mock_store, mock_log, failure_threshold=5, lookback_hours=24)


# ---------------------------------------------------------------------------
# HealthChecker tests
# ---------------------------------------------------------------------------


def test_healthy_when_failures_below_threshold(checker):
    status = checker.check()
    assert status.healthy is True
    assert status.recent_failures == 1
    assert status.total_jobs_tracked == 3


def test_unhealthy_when_failures_at_or_above_threshold(mock_store, mock_log):
    mock_store.recent_runs.return_value = [{"success": False}] * 5
    c = HealthChecker(mock_store, mock_log, failure_threshold=5)
    status = c.check()
    assert status.healthy is False


def test_last_notification_populated(checker, mock_log):
    status = checker.check()
    assert status.last_notification_at is not None


def test_last_notification_none_when_no_entries(mock_store, mock_log):
    mock_log.recent_entries.return_value = []
    c = HealthChecker(mock_store, mock_log)
    status = c.check()
    assert status.last_notification_at is None


def test_as_dict_contains_expected_keys(checker):
    d = checker.check().as_dict()
    assert "healthy" in d
    assert "checked_at" in d
    assert "total_jobs_tracked" in d
    assert "recent_failures" in d
    assert "last_notification_at" in d


# ---------------------------------------------------------------------------
# HealthServer tests
# ---------------------------------------------------------------------------


def test_health_server_start_and_stop(checker):
    server = HealthServer(checker, host="127.0.0.1", port=19876)
    server.start()
    assert server._thread is not None and server._thread.is_alive()
    server.stop()


def test_health_endpoint_returns_200_when_healthy(checker):
    import urllib.request

    server = HealthServer(checker, host="127.0.0.1", port=19877)
    server.start()
    try:
        with urllib.request.urlopen("http://127.0.0.1:19877/health") as resp:
            assert resp.status == 200
            data = json.loads(resp.read())
            assert data["healthy"] is True
    finally:
        server.stop()
