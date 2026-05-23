"""Handle alerting when a job attempts to run while in cooldown."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from cronwatcher.job_cooldown import CooldownChecker, CooldownViolation


@dataclass
class CooldownAlertResult:
    job_name: str
    violation: Optional[CooldownViolation]
    alerted: bool
    message: str


class CooldownAlertHandler:
    """Check jobs for cooldown violations and emit alert results."""

    def __init__(self, checker: CooldownChecker) -> None:
        self._checker = checker

    def handle(
        self,
        job_name: str,
        last_run_at: Optional[datetime],
    ) -> CooldownAlertResult:
        violation = self._checker.check(job_name, last_run_at)
        if violation is None:
            return CooldownAlertResult(
                job_name=job_name,
                violation=None,
                alerted=False,
                message=f"Job '{job_name}' is not in cooldown.",
            )
        return CooldownAlertResult(
            job_name=job_name,
            violation=violation,
            alerted=True,
            message=str(violation),
        )

    def handle_all(
        self,
        jobs: List[tuple[str, Optional[datetime]]],
    ) -> List[CooldownAlertResult]:
        """Process a list of (job_name, last_run_at) pairs."""
        results = []
        for job_name, last_run_at in jobs:
            results.append(self.handle(job_name, last_run_at))
        return results

    def violations(
        self,
        jobs: List[tuple[str, Optional[datetime]]],
    ) -> List[CooldownAlertResult]:
        """Return only results where a cooldown violation was detected."""
        return [
            r for r in self.handle_all(jobs) if r.alerted
        ]
