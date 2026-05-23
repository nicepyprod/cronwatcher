"""Lightweight in-process metrics collector for cronwatcher."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class JobMetrics:
    """Aggregated runtime metrics for a single cron job."""

    job_name: str
    run_count: int = 0
    failure_count: int = 0
    total_duration_seconds: float = 0.0
    last_run_ts: float = 0.0

    @property
    def avg_duration_seconds(self) -> float:
        if self.run_count == 0:
            return 0.0
        return self.total_duration_seconds / self.run_count

    @property
    def success_rate(self) -> float:
        if self.run_count == 0:
            return 1.0
        return (self.run_count - self.failure_count) / self.run_count

    def as_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "run_count": self.run_count,
            "failure_count": self.failure_count,
            "avg_duration_seconds": round(self.avg_duration_seconds, 3),
            "success_rate": round(self.success_rate, 4),
            "last_run_ts": self.last_run_ts,
        }


class MetricsCollector:
    """Thread-safe collector that accumulates job run metrics in memory."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._metrics: Dict[str, JobMetrics] = {}

    def record(self, job_name: str, duration_seconds: float, success: bool) -> None:
        """Record the outcome of a single job run."""
        with self._lock:
            if job_name not in self._metrics:
                self._metrics[job_name] = JobMetrics(job_name=job_name)
            m = self._metrics[job_name]
            m.run_count += 1
            if not success:
                m.failure_count += 1
            m.total_duration_seconds += duration_seconds
            m.last_run_ts = time.time()

    def get(self, job_name: str) -> JobMetrics | None:
        with self._lock:
            return self._metrics.get(job_name)

    def all(self) -> List[JobMetrics]:
        with self._lock:
            return list(self._metrics.values())

    def reset(self) -> None:
        """Clear all collected metrics (useful between test runs)."""
        with self._lock:
            self._metrics.clear()
