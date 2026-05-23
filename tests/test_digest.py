"""Tests for DigestSender and DigestScheduler."""

from __future__ import annotations

import smtplib
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.config import AlertConfig
from cronwatcher.digest import DigestSender
from cronwatcher.digest_scheduler import DigestScheduler
from cronwatcher.reporter import Report, JobSummary


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def alert_config() -> AlertConfig:
    return AlertConfig(
        enabled=True,
        smtp_host="localhost",
        smtp_port=1025,
        from_address="cron@example.com",
        recipients=["ops@example.com"],
        use_tls=False,
        username="",
        password="",
    )


@pytest.fixture()
def sample_report() -> Report:
    summary = JobSummary(
        job_name="backup",
        total_runs=10,
        successful_runs=9,
        failed_runs=1,
        avg_duration_seconds=42.0,
        last_run_at=datetime(2024, 1, 15, 3, 0, 0),
    )
    return Report(summaries=[summary], generated_at=datetime(2024, 1, 15, 6, 0, 0))


@pytest.fixture()
def mock_reporter(sample_report: Report) -> MagicMock:
    reporter = MagicMock()
    reporter.build.return_value = sample_report
    return reporter


# ---------------------------------------------------------------------------
# DigestSender tests
# ---------------------------------------------------------------------------

class TestDigestSender:
    def test_returns_false_when_alerts_disabled(self, mock_reporter, alert_config):
        alert_config.enabled = False
        sender = DigestSender(mock_reporter, alert_config)
        assert sender.send() is False
        mock_reporter.build.assert_not_called()

    def test_returns_true_on_success(self, mock_reporter, alert_config):
        sender = DigestSender(mock_reporter, alert_config)
        with patch("smtplib.SMTP") as mock_smtp:
            instance = mock_smtp.return_value.__enter__.return_value
            instance.sendmail.return_value = {}
            result = sender.send(now=datetime(2024, 1, 15, 6, 0, 0))
        assert result is True

    def test_returns_false_on_smtp_error(self, mock_reporter, alert_config):
        sender = DigestSender(mock_reporter, alert_config)
        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__.side_effect = smtplib.SMTPException("boom")
            result = sender.send()
        assert result is False

    def test_reporter_receives_time_window(self, mock_reporter, alert_config):
        sender = DigestSender(mock_reporter, alert_config, window_hours=12)
        now = datetime(2024, 1, 15, 12, 0, 0)
        with patch("smtplib.SMTP"):
            sender.send(now=now)
        call_kwargs = mock_reporter.build.call_args
        assert call_kwargs is not None
        since = call_kwargs.kwargs["since"]
        assert (now - since).total_seconds() == pytest.approx(12 * 3600)


# ---------------------------------------------------------------------------
# DigestScheduler tests
# ---------------------------------------------------------------------------

class TestDigestScheduler:
    def test_sends_on_first_tick(self):
        sender = MagicMock()
        sender.send.return_value = True
        scheduler = DigestScheduler(sender, interval_seconds=3600, tick_seconds=1)
        scheduler._maybe_send()
        sender.send.assert_called_once()

    def test_does_not_resend_before_interval(self):
        sender = MagicMock()
        sender.send.return_value = True
        scheduler = DigestScheduler(sender, interval_seconds=3600)
        scheduler._maybe_send()  # first send sets _last_sent
        scheduler._maybe_send()  # should be skipped
        assert sender.send.call_count == 1

    def test_resends_after_interval(self):
        from datetime import timedelta
        sender = MagicMock()
        sender.send.return_value = True
        scheduler = DigestScheduler(sender, interval_seconds=3600)
        scheduler._maybe_send()
        # Wind back last_sent to simulate interval elapsed
        scheduler._last_sent = scheduler._last_sent - timedelta(hours=2)
        scheduler._maybe_send()
        assert sender.send.call_count == 2
