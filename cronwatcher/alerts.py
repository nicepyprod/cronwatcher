"""Alert sending module for cronwatcher."""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass
from typing import Optional

from cronwatcher.config import AlertConfig

logger = logging.getLogger(__name__)


@dataclass
class AlertEvent:
    job_name: str
    event_type: str  # 'failure' | 'missed' | 'duration_exceeded'
    message: str
    duration_seconds: Optional[float] = None
    exit_code: Optional[int] = None


class AlertSender:
    def __init__(self, config: AlertConfig):
        self.config = config

    def send(self, event: AlertEvent) -> bool:
        """Send an alert for the given event. Returns True on success."""
        if not self.config.enabled:
            logger.debug("Alerts disabled; skipping alert for job '%s'", event.job_name)
            return False

        subject = self._build_subject(event)
        body = self._build_body(event)

        try:
            self._send_email(subject, body)
            logger.info("Alert sent for job '%s' (%s)", event.job_name, event.event_type)
            return True
        except Exception as exc:
            logger.error("Failed to send alert for job '%s': %s", event.job_name, exc)
            return False

    def _build_subject(self, event: AlertEvent) -> str:
        type_labels = {
            "failure": "FAILURE",
            "missed": "MISSED RUN",
            "duration_exceeded": "DURATION EXCEEDED",
        }
        label = type_labels.get(event.event_type, event.event_type.upper())
        return f"[cronwatcher] {label}: {event.job_name}"

    def _build_body(self, event: AlertEvent) -> str:
        lines = [
            f"Job: {event.job_name}",
            f"Event: {event.event_type}",
            f"Details: {event.message}",
        ]
        if event.duration_seconds is not None:
            lines.append(f"Duration: {event.duration_seconds:.2f}s")
        if event.exit_code is not None:
            lines.append(f"Exit code: {event.exit_code}")
        return "\n".join(lines)

    def _send_email(self, subject: str, body: str) -> None:
        msg = MIMEMultipart()
        msg["From"] = self.config.from_email
        msg["To"] = ", ".join(self.config.recipients)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
            if self.config.smtp_use_tls:
                server.starttls()
            if self.config.smtp_username and self.config.smtp_password:
                server.login(self.config.smtp_username, self.config.smtp_password)
            server.sendmail(self.config.from_email, self.config.recipients, msg.as_string())
