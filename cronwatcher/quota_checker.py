"""Checks whether jobs have exceeded their configured run quotas."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol

from cronwatcher.job_quota import JobQuotaStore, QuotaEntry, QuotaViolation


class RunCountProvider(Protocol):
    """Minimal interface needed to count recent job runs."""

    def count_runs_since(self, job_name: str, since: datetime) -> int:
        ...


class QuotaChecker:
    """Evaluates run quotas for all configured jobs."""

    def __init__(self, quota_store: JobQuotaStore, run_store: RunCountProvider) -> None:
        self._quotas = quota_store
        self._runs = run_store

    def check(self, job_name: str) -> QuotaViolation | None:
        """Return a QuotaViolation if the job has exceeded its quota, else None."""
        entry = self._quotas.get_quota(job_name)
        if entry is None:
            return None
        return self._evaluate(entry)

    def check_all(self) -> list[QuotaViolation]:
        """Return violations for every job that has a quota defined."""
        violations: list[QuotaViolation] = []
        for entry in self._quotas.all_quotas():
            violation = self._evaluate(entry)
            if violation is not None:
                violations.append(violation)
        return violations

    def is_allowed(self, job_name: str) -> bool:
        """Return True when the job is within its quota (or has no quota)."""
        return self.check(job_name) is None

    # ------------------------------------------------------------------
    def _evaluate(self, entry: QuotaEntry) -> QuotaViolation | None:
        since = datetime.now(tz=timezone.utc) - timedelta(seconds=entry.window_seconds)
        count = self._runs.count_runs_since(entry.job_name, since)
        if count > entry.max_runs:
            return QuotaViolation(
                job_name=entry.job_name,
                window_seconds=entry.window_seconds,
                max_runs=entry.max_runs,
                actual_runs=count,
            )
        return None
