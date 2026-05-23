"""Tests for cronwatcher.notifier."""

from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.alerts import AlertEvent
from cronwatcher.config import AlertConfig
from cronwatcher.notifier import Notifier, Severity, severity_for_event


@pytest.fixture()
def alert_config():
    return AlertConfig(
        enabled=True,
        smtp_host="localhost",
        smtp_port=25,
        from_addr="cron@example.com",
        to_addrs=["ops@example.com"],
    )


def _event(exit_code=None, missed=False):
    return AlertEvent(job_name="backup", exit_code=exit_code, missed=missed, duration=1.0)


class TestSeverityForEvent:
    def test_non_zero_exit_is_critical(self):
        assert severity_for_event(_event(exit_code=1)) == Severity.CRITICAL

    def test_missed_is_warning(self):
        assert severity_for_event(_event(missed=True)) == Severity.WARNING

    def test_success_is_info(self):
        assert severity_for_event(_event(exit_code=0)) == Severity.INFO


class TestNotifier:
    def test_sends_when_severity_meets_threshold(self, alert_config):
        notifier = Notifier(alert_config, min_severity=Severity.WARNING)
        with patch("cronwatcher.notifier.AlertSender.send", return_value=True):
            result = notifier.notify(_event(exit_code=1))
        assert result.sent is True
        assert result.severity == Severity.CRITICAL

    def test_skips_below_threshold(self, alert_config):
        notifier = Notifier(alert_config, min_severity=Severity.WARNING)
        with patch("cronwatcher.notifier.AlertSender.send") as mock_send:
            result = notifier.notify(_event(exit_code=0))
        mock_send.assert_not_called()
        assert result.sent is False

    def test_warning_meets_warning_threshold(self, alert_config):
        notifier = Notifier(alert_config, min_severity=Severity.WARNING)
        with patch("cronwatcher.notifier.AlertSender.send", return_value=True):
            result = notifier.notify(_event(missed=True))
        assert result.sent is True
        assert result.severity == Severity.WARNING

    def test_all_sent_when_min_severity_info(self, alert_config):
        notifier = Notifier(alert_config, min_severity=Severity.INFO)
        with patch("cronwatcher.notifier.AlertSender.send", return_value=True):
            result = notifier.notify(_event(exit_code=0))
        assert result.sent is True
