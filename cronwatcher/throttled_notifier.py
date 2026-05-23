"""Notifier wrapper that applies rate limiting before dispatching alerts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from cronwatcher.alerts import AlertEvent
from cronwatcher.notifier import NotificationResult, Notifier
from cronwatcher.rate_limiter import AlertRateLimiter


@dataclass
class ThrottledResult:
    event: AlertEvent
    suppressed: bool
    result: NotificationResult | None


class ThrottledNotifier:
    """Wraps a Notifier with rate-limiting so repeated alerts are suppressed."""

    def __init__(
        self,
        notifier: Notifier,
        rate_limiter: AlertRateLimiter,
    ) -> None:
        self._notifier = notifier
        self._limiter = rate_limiter

    def notify(self, event: AlertEvent) -> ThrottledResult:
        """Send alert only if not within cooldown window."""
        alert_type = event.reason
        job_name = event.job_name

        if not self._limiter.is_allowed(job_name, alert_type):
            return ThrottledResult(event=event, suppressed=True, result=None)

        result = self._notifier.notify(event)
        if result.success:
            self._limiter.record_sent(job_name, alert_type)
        return ThrottledResult(event=event, suppressed=False, result=result)

    def notify_many(self, events: List[AlertEvent]) -> List[ThrottledResult]:
        """Process a list of events, applying rate limiting to each."""
        return [self.notify(e) for e in events]

    def reset_cooldown(self, job_name: str, alert_type: str) -> None:
        """Manually clear the cooldown for a job/alert-type pair."""
        self._limiter.clear(job_name, alert_type)
