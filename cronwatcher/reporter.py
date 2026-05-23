"""Generates summary reports of cron job execution history."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from cronwatcher.db import JobRunStore


@dataclass
class JobSummary:
    job_name: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    avg_duration_seconds: Optional[float]
    last_run_at: Optional[datetime]
    last_status: Optional[str]

    @property
    def success_rate(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return self.successful_runs / self.total_runs * 100


@dataclass
class Report:
    generated_at: datetime
    period_hours: int
    summaries: List[JobSummary]

    @property
    def total_jobs(self) -> int:
        return len(self.summaries)

    @property
    def jobs_with_failures(self) -> List[JobSummary]:
        return [s for s in self.summaries if s.failed_runs > 0]


class Reporter:
    def __init__(self, store: JobRunStore):
        self._store = store

    def generate(self, job_names: List[str], period_hours: int = 24) -> Report:
        since = datetime.utcnow() - timedelta(hours=period_hours)
        summaries = [
            self._summarize(name, since) for name in job_names
        ]
        return Report(
            generated_at=datetime.utcnow(),
            period_hours=period_hours,
            summaries=summaries,
        )

    def _summarize(self, job_name: str, since: datetime) -> JobSummary:
        rows = self._store.get_runs_since(job_name, since)
        total = len(rows)
        successful = sum(1 for r in rows if r["status"] == "success")
        failed = sum(1 for r in rows if r["status"] == "failure")
        durations = [r["duration_seconds"] for r in rows if r["duration_seconds"] is not None]
        avg_duration = sum(durations) / len(durations) if durations else None
        last_row = rows[-1] if rows else None
        last_run_at = datetime.fromisoformat(last_row["started_at"]) if last_row else None
        last_status = last_row["status"] if last_row else None
        return JobSummary(
            job_name=job_name,
            total_runs=total,
            successful_runs=successful,
            failed_runs=failed,
            avg_duration_seconds=avg_duration,
            last_run_at=last_run_at,
            last_status=last_status,
        )
