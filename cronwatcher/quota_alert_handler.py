"""Handles quota violations by emitting alert events through the notification pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from cronwatcher.job_quota import QuotaViolation
from cronwatcher.notifier import AlertEvent, Notifier
from cronwatcher.quota_checker import QuotaChecker


@dataclass
class QuotaAlertResult:
    job_name: str
    violation: QuotaViolation
    notified: bool


class QuotaAlertHandler:
    """Checks all job quotas and fires alerts for any violations found."""

    def __init__(self, checker: QuotaChecker, notifier: Notifier) -> None:
        self._checker = checker
        self._notifier = notifier

    def handle_all(self) -> list[QuotaAlertResult]:
        """Run quota check across all jobs and send alerts for violations."""
        violations = self._checker.check_all()
        results: list[QuotaAlertResult] = []
        for violation in violations:
            event = self._build_event(violation)
            result = self._notifier.notify(event)
            results.append(
                QuotaAlertResult(
                    job_name=violation.job_name,
                    violation=violation,
                    notified=result.sent,
                )
            )
        return results

    def handle_job(self, job_name: str) -> QuotaAlertResult | None:
        """Check quota for a single job and alert if violated."""
        violation = self._checker.check(job_name)
        if violation is None:
            return None
        event = self._build_event(violation)
        result = self._notifier.notify(event)
        return QuotaAlertResult(
            job_name=job_name,
            violation=violation,
            notified=result.sent,
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _build_event(violation: QuotaViolation) -> AlertEvent:
        return AlertEvent(
            job_name=violation.job_name,
            event_type="quota_exceeded",
            message=str(violation),
            exit_code=None,
        )
