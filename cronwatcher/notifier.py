"""Notification routing: decides which alert channels to use based on event severity."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List

from cronwatcher.alerts import AlertEvent, AlertSender
from cronwatcher.config import AlertConfig

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


def severity_for_event(event: AlertEvent) -> Severity:
    """Determine severity level from an AlertEvent."""
    if event.exit_code is not None and event.exit_code != 0:
        return Severity.CRITICAL
    if event.missed:
        return Severity.WARNING
    return Severity.INFO


@dataclass
class NotificationResult:
    event: AlertEvent
    severity: Severity
    sent: bool
    errors: List[str] = field(default_factory=list)


class Notifier:
    """Routes alert events through configured senders based on severity."""

    def __init__(self, alert_config: AlertConfig, min_severity: Severity = Severity.WARNING):
        self._sender = AlertSender(alert_config)
        self._min_severity = min_severity

    def notify(self, event: AlertEvent) -> NotificationResult:
        severity = severity_for_event(event)
        if not self._should_send(severity):
            logger.debug("Skipping notification for %s (severity=%s)", event.job_name, severity)
            return NotificationResult(event=event, severity=severity, sent=False)

        try:
            sent = self._sender.send(event)
            return NotificationResult(event=event, severity=severity, sent=sent)
        except Exception as exc:  # pragma: no cover
            logger.error("Unexpected error sending notification: %s", exc)
            return NotificationResult(event=event, severity=severity, sent=False, errors=[str(exc)])

    def _should_send(self, severity: Severity) -> bool:
        order = [Severity.INFO, Severity.WARNING, Severity.CRITICAL]
        return order.index(severity) >= order.index(self._min_severity)
