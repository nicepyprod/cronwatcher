"""Provides a per-job run history view with recent executions and trend data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from cronwatcher.db import JobRunStore


@dataclass
class RunRecord:
    run_id: int
    job_name: str
    started_at: float
    finished_at: Optional[float]
    exit_code: Optional[int]
    duration_seconds: Optional[float]

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0


@dataclass
class JobHistory:
    job_name: str
    runs: List[RunRecord] = field(default_factory=list)

    @property
    def total_runs(self) -> int:
        return len(self.runs)

    @property
    def successful_runs(self) -> int:
        return sum(1 for r in self.runs if r.succeeded)

    @property
    def failed_runs(self) -> int:
        return sum(1 for r in self.runs if r.exit_code is not None and not r.succeeded)

    @property
    def success_rate(self) -> float:
        finished = [r for r in self.runs if r.exit_code is not None]
        if not finished:
            return 1.0
        return sum(1 for r in finished if r.succeeded) / len(finished)

    @property
    def avg_duration_seconds(self) -> Optional[float]:
        durations = [r.duration_seconds for r in self.runs if r.duration_seconds is not None]
        if not durations:
            return None
        return sum(durations) / len(durations)

    @property
    def last_run(self) -> Optional[RunRecord]:
        return self.runs[0] if self.runs else None


class JobHistoryReader:
    """Reads run history for individual jobs from the JobRunStore."""

    def __init__(self, store: JobRunStore) -> None:
        self._store = store

    def get_history(self, job_name: str, limit: int = 20) -> JobHistory:
        rows = self._store.recent_runs(job_name, limit=limit)
        records = [
            RunRecord(
                run_id=row["id"],
                job_name=row["job_name"],
                started_at=row["started_at"],
                finished_at=row.get("finished_at"),
                exit_code=row.get("exit_code"),
                duration_seconds=row.get("duration_seconds"),
            )
            for row in rows
        ]
        return JobHistory(job_name=job_name, runs=records)

    def get_histories(self, job_names: List[str], limit: int = 20) -> List[JobHistory]:
        return [self.get_history(name, limit=limit) for name in job_names]
