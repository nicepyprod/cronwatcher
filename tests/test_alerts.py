"""Tests for cronwatcher.alerts module."""

import pytest
from unittest.mock import MagicMock, patch

from cronwatcher.alerts import AlertSender, AlertEvent
from cronwatcher.config import AlertConfig


@pytest.fixture
def alert_config():
    return AlertConfig(
        enabled=True,
        recipients=["ops@example.com"],
        from_email="cronwatcher@example.com",
        smtp_host="localhost",
        smtp_port=25,
        smtp_use_tls=False,
        smtp_username=None,
        smtp_password=None,
    )


@pytest.fixture
def failure_event():
    return AlertEvent(
        job_name="backup",
        event_type="failure",
        message="Job exited with code 1",
        exit_code=1,
        duration_seconds=3.5,
    )


def test_send_returns_false_when_alerts_disabled(failure_event):
    config = AlertConfig(
        enabled=False,
        recipients=["ops@example.com"],
        from_email="cronwatcher@example.com",
        smtp_host="localhost",
        smtp_port=25,
    )
    sender = AlertSender(config)
    assert sender.send(failure_event) is False


def test_send_returns_true_on_success(alert_config, failure_event):
    sender = AlertSender(alert_config)
    with patch("cronwatcher.alerts.smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        result = sender.send(failure_event)
    assert result is True
    mock_server.sendmail.assert_called_once()


def test_send_returns_false_on_smtp_error(alert_config, failure_event):
    sender = AlertSender(alert_config)
    with patch("cronwatcher.alerts.smtplib.SMTP", side_effect=ConnectionRefusedError("refused")):
        result = sender.send(failure_event)
    assert result is False


def test_subject_contains_job_name_and_event_type(alert_config, failure_event):
    sender = AlertSender(alert_config)
    subject = sender._build_subject(failure_event)
    assert "backup" in subject
    assert "FAILURE" in subject


def test_subject_for_missed_run(alert_config):
    sender = AlertSender(alert_config)
    event = AlertEvent(job_name="report", event_type="missed", message="No run in 2h")
    subject = sender._build_subject(event)
    assert "MISSED RUN" in subject
    assert "report" in subject


def test_body_includes_duration_and_exit_code(alert_config, failure_event):
    sender = AlertSender(alert_config)
    body = sender._build_body(failure_event)
    assert "3.50s" in body
    assert "Exit code: 1" in body
    assert "backup" in body


def test_body_omits_optional_fields_when_none(alert_config):
    sender = AlertSender(alert_config)
    event = AlertEvent(job_name="cleanup", event_type="missed", message="Overdue")
    body = sender._build_body(event)
    assert "Duration" not in body
    assert "Exit code" not in body
