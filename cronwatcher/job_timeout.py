"""Detects jobs that have been running longer than their configured timeout."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from cronwatcher.config import JobConfig
from cronwatcher.db import JobRunStore


@dataclass
class TimeoutViolation:
    job_name: str
    run_id: int
    started_at: datetime
    running_for_seconds: float
    timeout_seconds: int

    def __str__(self) -> str:
        return (
            f"{self.job_name} (run_id={self.run_id}) has been running for "
            f"{self.running_for_seconds:.1f}s, timeout={self.timeout_seconds}s"
        )


class JobTimeoutChecker:
    """Checks for jobs that have exceeded their maximum allowed run duration."""

    def __init__(self, store: JobRunStore, jobs: List[JobConfig]) -> None:
        self._store = store
        self._jobs: dict[str, JobConfig] = {j.name: j for j in jobs}

    def check(self, now: Optional[datetime] = None) -> List[TimeoutViolation]:
        """Return a list of TimeoutViolation for any currently-running jobs
        that have exceeded their configured timeout_seconds."""
        if now is None:
            now = datetime.now(timezone.utc)

        violations: List[TimeoutViolation] = []
        running = self._store.get_running_runs()

        for run in running:
            job_cfg = self._jobs.get(run["job_name"])
            if job_cfg is None or job_cfg.timeout_seconds is None:
                continue

            started_at: datetime = run["started_at"]
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)

            elapsed = (now - started_at).total_seconds()
            if elapsed > job_cfg.timeout_seconds:
                violations.append(
                    TimeoutViolation(
                        job_name=run["job_name"],
                        run_id=run["run_id"],
                        started_at=started_at,
                        running_for_seconds=elapsed,
                        timeout_seconds=job_cfg.timeout_seconds,
                    )
                )

        return violations
