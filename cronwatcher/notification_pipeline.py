"""High-level pipeline: notify + log the result."""

from __future__ import annotations

import logging
from typing import List

from cronwatcher.alerts import AlertEvent
from cronwatcher.notifier import NotificationResult, Notifier, Severity
from cronwatcher.notification_log import NotificationLog

logger = logging.getLogger(__name__)


class NotificationPipeline:
    """Combines Notifier and NotificationLog into a single send-and-record step."""

    def __init__(self, notifier: Notifier, log: NotificationLog):
        self._notifier = notifier
        self._log = log

    def process(self, event: AlertEvent) -> NotificationResult:
        result = self._notifier.notify(event)
        self._log.record(
            job_name=event.job_name,
            severity=result.severity.value,
            success=result.sent,
            error="; ".join(result.errors),
        )
        logger.info(
            "Notification pipeline: job=%s severity=%s sent=%s",
            event.job_name, result.severity, result.sent,
        )
        return result

    def process_many(self, events: List[AlertEvent]) -> List[NotificationResult]:
        return [self.process(e) for e in events]

    def recent_log(self, job_name: str, limit: int = 10):
        return self._log.recent(job_name, limit)
