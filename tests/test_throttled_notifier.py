"""Tests for cronwatcher.throttled_notifier."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cronwatcher.alerts import AlertEvent
from cronwatcher.notifier import NotificationResult
from cronwatcher.rate_limiter import AlertRateLimiter
from cronwatcher.throttled_notifier import ThrottledNotifier


@pytest.fixture
def rate_limiter() -> AlertRateLimiter:
    return AlertRateLimiter(db_path=":memory:", cooldown_seconds=3600)


@pytest.fixture
def mock_notifier() -> MagicMock:
    notifier = MagicMock()
    notifier.notify.return_value = NotificationResult(success=True, message="ok")
    return notifier


@pytest.fixture
def throttled(mock_notifier, rate_limiter) -> ThrottledNotifier:
    return ThrottledNotifier(notifier=mock_notifier, rate_limiter=rate_limiter)


def _event(job_name: str = "backup", reason: str = "failure") -> AlertEvent:
    return AlertEvent(job_name=job_name, reason=reason, detail="exit code 1")


class TestThrottledNotifier:
    def test_first_alert_is_sent(self, throttled, mock_notifier) -> None:
        result = throttled.notify(_event())
        assert result.suppressed is False
        mock_notifier.notify.assert_called_once()

    def test_second_alert_is_suppressed(self, throttled, mock_notifier) -> None:
        throttled.notify(_event())
        result = throttled.notify(_event())
        assert result.suppressed is True
        assert mock_notifier.notify.call_count == 1

    def test_suppressed_result_has_no_inner_result(self, throttled) -> None:
        throttled.notify(_event())
        result = throttled.notify(_event())
        assert result.result is None

    def test_different_jobs_not_suppressed(self, throttled, mock_notifier) -> None:
        throttled.notify(_event(job_name="backup"))
        result = throttled.notify(_event(job_name="sync"))
        assert result.suppressed is False
        assert mock_notifier.notify.call_count == 2

    def test_reset_cooldown_allows_resend(self, throttled, mock_notifier) -> None:
        throttled.notify(_event())
        throttled.reset_cooldown("backup", "failure")
        result = throttled.notify(_event())
        assert result.suppressed is False
        assert mock_notifier.notify.call_count == 2

    def test_notify_many_processes_all_events(self, throttled, mock_notifier) -> None:
        events = [_event("job1"), _event("job2"), _event("job3")]
        results = throttled.notify_many(events)
        assert len(results) == 3
        assert all(not r.suppressed for r in results)

    def test_failed_send_does_not_record_cooldown(self, rate_limiter) -> None:
        failing_notifier = MagicMock()
        failing_notifier.notify.return_value = NotificationResult(success=False, message="err")
        throttled = ThrottledNotifier(notifier=failing_notifier, rate_limiter=rate_limiter)
        throttled.notify(_event())
        # Should be allowed again because previous send failed
        assert rate_limiter.is_allowed("backup", "failure") is True
