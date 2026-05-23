"""Tests for JobTimeoutChecker and JobTimeoutHandler."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.config import JobConfig
from cronwatcher.job_timeout import JobTimeoutChecker, TimeoutViolation
from cronwatcher.job_timeout_handler import JobTimeoutHandler


def _job(name: str, timeout: int) -> JobConfig:
    return JobConfig(name=name, schedule="* * * * *", timeout_seconds=timeout)


def _run(name: str, started_seconds_ago: float, run_id: int = 1) -> dict:
    started = datetime.now(timezone.utc) - timedelta(seconds=started_seconds_ago)
    return {"job_name": name, "run_id": run_id, "started_at": started}


@pytest.fixture
def store():
    return MagicMock()


class TestJobTimeoutChecker:
    def test_no_violations_when_no_running_jobs(self, store):
        store.get_running_runs.return_value = []
        checker = JobTimeoutChecker(store, [_job("backup", 60)])
        assert checker.check() == []

    def test_no_violation_when_within_timeout(self, store):
        store.get_running_runs.return_value = [_run("backup", started_seconds_ago=30)]
        checker = JobTimeoutChecker(store, [_job("backup", 60)])
        assert checker.check() == []

    def test_violation_when_exceeds_timeout(self, store):
        store.get_running_runs.return_value = [_run("backup", started_seconds_ago=120, run_id=7)]
        checker = JobTimeoutChecker(store, [_job("backup", 60)])
        violations = checker.check()
        assert len(violations) == 1
        v = violations[0]
        assert v.job_name == "backup"
        assert v.run_id == 7
        assert v.timeout_seconds == 60
        assert v.running_for_seconds >= 120

    def test_skips_jobs_without_timeout_config(self, store):
        job = JobConfig(name="nolimit", schedule="* * * * *", timeout_seconds=None)
        store.get_running_runs.return_value = [_run("nolimit", started_seconds_ago=9999)]
        checker = JobTimeoutChecker(store, [job])
        assert checker.check() == []

    def test_skips_unknown_jobs(self, store):
        store.get_running_runs.return_value = [_run("unknown", started_seconds_ago=999)]
        checker = JobTimeoutChecker(store, [_job("backup", 60)])
        assert checker.check() == []

    def test_violation_str_contains_job_name(self, store):
        store.get_running_runs.return_value = [_run("cleanup", started_seconds_ago=200, run_id=3)]
        checker = JobTimeoutChecker(store, [_job("cleanup", 100)])
        violations = checker.check()
        assert "cleanup" in str(violations[0])


class TestJobTimeoutHandler:
    def test_handle_calls_notifier_for_each_violation(self, store):
        store.get_running_runs.return_value = [
            _run("job_a", 200, run_id=1),
            _run("job_b", 300, run_id=2),
        ]
        checker = JobTimeoutChecker(store, [_job("job_a", 60), _job("job_b", 60)])
        notifier = MagicMock()
        handler = JobTimeoutHandler(checker, notifier)
        violations = handler.handle()
        assert len(violations) == 2
        assert notifier.notify.call_count == 2

    def test_handle_returns_empty_when_no_violations(self, store):
        store.get_running_runs.return_value = []
        checker = JobTimeoutChecker(store, [_job("job_a", 60)])
        notifier = MagicMock()
        handler = JobTimeoutHandler(checker, notifier)
        assert handler.handle() == []
        notifier.notify.assert_not_called()

    def test_alert_event_type_is_timeout(self, store):
        store.get_running_runs.return_value = [_run("sync", 500, run_id=9)]
        checker = JobTimeoutChecker(store, [_job("sync", 60)])
        notifier = MagicMock()
        handler = JobTimeoutHandler(checker, notifier)
        handler.handle()
        event = notifier.notify.call_args[0][0]
        assert event.event_type == "timeout"
        assert event.job_name == "sync"
