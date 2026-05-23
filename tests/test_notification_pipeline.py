"""Tests for cronwatcher.notification_pipeline and cronwatcher.notification_log."""

from unittest.mock import MagicMock

import pytest

from cronwatcher.alerts import AlertEvent
from cronwatcher.notification_log import NotificationLog
from cronwatcher.notification_pipeline import NotificationPipeline
from cronwatcher.notifier import NotificationResult, Severity


@pytest.fixture()
def log():
    return NotificationLog(db_path=":memory:")


@pytest.fixture()
def notifier_mock():
    return MagicMock()


@pytest.fixture()
def pipeline(notifier_mock, log):
    return NotificationPipeline(notifier=notifier_mock, log=log)


def _event(job_name="backup", exit_code=1, missed=False):
    return AlertEvent(job_name=job_name, exit_code=exit_code, missed=missed, duration=2.5)


class TestNotificationLog:
    def test_record_and_retrieve(self, log):
        log.record("backup", "critical", success=True)
        entries = log.recent("backup")
        assert len(entries) == 1
        assert entries[0].job_name == "backup"
        assert entries[0].severity == "critical"
        assert entries[0].success is True

    def test_recent_respects_limit(self, log):
        for _ in range(5):
            log.record("job", "warning", success=False)
        assert len(log.recent("job", limit=3)) == 3

    def test_recent_filters_by_job(self, log):
        log.record("jobA", "critical", success=True)
        log.record("jobB", "warning", success=False)
        assert len(log.recent("jobA")) == 1


class TestNotificationPipeline:
    def test_process_records_success(self, pipeline, notifier_mock, log):
        event = _event()
        notifier_mock.notify.return_value = NotificationResult(
            event=event, severity=Severity.CRITICAL, sent=True
        )
        result = pipeline.process(event)
        assert result.sent is True
        entries = log.recent("backup")
        assert len(entries) == 1
        assert entries[0].success is True

    def test_process_many(self, pipeline, notifier_mock, log):
        events = [_event(job_name=f"job{i}") for i in range(3)]
        notifier_mock.notify.return_value = NotificationResult(
            event=events[0], severity=Severity.CRITICAL, sent=True
        )
        results = pipeline.process_many(events)
        assert len(results) == 3

    def test_recent_log_delegates_to_log(self, pipeline, log):
        log.record("backup", "critical", success=True)
        entries = pipeline.recent_log("backup")
        assert len(entries) == 1
