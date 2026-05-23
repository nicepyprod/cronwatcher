"""Periodic digest sender: builds a report and emails it on a schedule."""

from __future__ import annotations

import logging
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from cronwatcher.config import AlertConfig
from cronwatcher.reporter import Reporter
from cronwatcher.report_formatter import TextFormatter, HtmlFormatter

logger = logging.getLogger(__name__)


class DigestSender:
    """Builds and sends a periodic digest email covering the last *window_hours*."""

    def __init__(self, reporter: Reporter, alert_config: AlertConfig, window_hours: int = 24) -> None:
        self._reporter = reporter
        self._cfg = alert_config
        self._window_hours = window_hours

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send(self, now: datetime | None = None) -> bool:
        """Generate a digest for the last window and send it.  Returns True on success."""
        if not self._cfg.enabled:
            logger.debug("Alerts disabled – skipping digest.")
            return False

        now = now or datetime.utcnow()
        since = now - timedelta(hours=self._window_hours)

        report = self._reporter.build(since=since, until=now)

        subject = self._build_subject(now)
        text_body = TextFormatter().format(report)
        html_body = HtmlFormatter().format(report)

        return self._send_email(subject, text_body, html_body)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_subject(self, now: datetime) -> str:
        return (
            f"[cronwatcher] Digest for {now.strftime('%Y-%m-%d %H:%M')} UTC "
            f"(last {self._window_hours}h)"
        )

    def _send_email(self, subject: str, text_body: str, html_body: str) -> bool:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._cfg.from_address
        msg["To"] = ", ".join(self._cfg.recipients)
        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        try:
            with smtplib.SMTP(self._cfg.smtp_host, self._cfg.smtp_port, timeout=10) as server:
                if self._cfg.use_tls:
                    server.starttls()
                if self._cfg.username:
                    server.login(self._cfg.username, self._cfg.password)
                server.sendmail(self._cfg.from_address, self._cfg.recipients, msg.as_string())
            logger.info("Digest sent to %s", self._cfg.recipients)
            return True
        except smtplib.SMTPException as exc:
            logger.error("Failed to send digest: %s", exc)
            return False
