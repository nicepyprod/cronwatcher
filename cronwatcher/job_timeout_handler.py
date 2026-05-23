"""Integrates JobTimeoutChecker with the alert pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from cronwatcher.alerts import AlertEvent
from cronwatcher.job_timeout import JobTimeoutChecker, TimeoutViolation
from cronwatcher.notifier import Notifier


class JobTimeoutHandler:
    """Runs timeout checks and dispatches alert events for each violation."""

    def __init__(self, checker: JobTimeoutChecker, notifier: Notifier) -> None:
        self._checker = checker
        self._notifier = notifier

    def handle(self, now: Optional[datetime] = None) -> List[TimeoutViolation]:
        """Check for timeout violations and send an alert for each one.

        Returns the list of violations found.
        """
        if now is None:
            now = datetime.now(timezone.utc)

        violations = self._checker.check(now=now)
        for v in violations:
            event = AlertEvent(
                job_name=v.job_name,
                event_type="timeout",
                message=(
                    f"Job '{v.job_name}' has been running for "
                    f"{v.running_for_seconds:.1f}s, "
                    f"exceeding timeout of {v.timeout_seconds}s."
                ),
                exit_code=None,
                run_id=v.run_id,
                occurred_at=now,
            )
            self._notifier.notify(event)

        return violations
