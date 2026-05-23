"""Check whether job dependencies have been satisfied before a run starts."""

from __future__ import annotations

from typing import List, Optional

from cronwatcher.job_dependencies import DependencyViolation, JobDependencyStore


class DependencyChecker:
    """Verify that all upstream jobs finished successfully before *job_name* runs."""

    def __init__(self, dep_store: JobDependencyStore, run_store) -> None:
        """
        Parameters
        ----------
        dep_store:
            A :class:`JobDependencyStore` instance.
        run_store:
            A :class:`~cronwatcher.db.JobRunStore` instance (duck-typed).
            Must expose ``latest_run(job_name) -> Optional[dict]`` where the
            dict contains at least ``status`` ("success" | "failure") and
            ``finished_at`` (datetime or None).
        """
        self._deps = dep_store
        self._runs = run_store

    def check(self, job_name: str) -> List[DependencyViolation]:
        """Return a list of violations; empty list means all deps satisfied."""
        violations: List[DependencyViolation] = []
        for dep in self._deps.get_dependencies(job_name):
            latest = self._runs.latest_run(dep)
            if latest is None:
                violations.append(
                    DependencyViolation(
                        job_name=job_name,
                        depends_on=dep,
                        reason="upstream job has never run",
                    )
                )
            elif latest.get("finished_at") is None:
                violations.append(
                    DependencyViolation(
                        job_name=job_name,
                        depends_on=dep,
                        reason="upstream job is still running",
                    )
                )
            elif latest.get("status") != "success":
                status = latest.get("status", "unknown")
                violations.append(
                    DependencyViolation(
                        job_name=job_name,
                        depends_on=dep,
                        reason=f"upstream job last finished with status '{status}'",
                    )
                )
        return violations

    def is_satisfied(self, job_name: str) -> bool:
        """Return True only when every dependency is satisfied."""
        return len(self.check(job_name)) == 0
