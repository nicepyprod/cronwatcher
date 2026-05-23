"""Health check endpoint for cronwatcher daemon status."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from cronwatcher.db import JobRunStore
from cronwatcher.notification_log import NotificationLog


@dataclass
class HealthStatus:
    healthy: bool
    checked_at: datetime
    total_jobs_tracked: int
    recent_failures: int
    last_notification_at: Optional[datetime]
    details: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "healthy": self.healthy,
            "checked_at": self.checked_at.isoformat(),
            "total_jobs_tracked": self.total_jobs_tracked,
            "recent_failures": self.recent_failures,
            "last_notification_at": (
                self.last_notification_at.isoformat()
                if self.last_notification_at
                else None
            ),
            "details": self.details,
        }


class HealthChecker:
    """Aggregates runtime metrics to produce a health snapshot."""

    def __init__(
        self,
        store: JobRunStore,
        notification_log: NotificationLog,
        failure_threshold: int = 5,
        lookback_hours: int = 24,
    ) -> None:
        self._store = store
        self._log = notification_log
        self._failure_threshold = failure_threshold
        self._lookback_hours = lookback_hours

    def check(self) -> HealthStatus:
        now = datetime.now(timezone.utc)
        recent_runs = self._store.recent_runs(hours=self._lookback_hours)
        total = len(recent_runs)
        failures = sum(1 for r in recent_runs if not r.get("success", True))

        entries = self._log.recent_entries(limit=1)
        last_notif = entries[0].sent_at if entries else None

        healthy = failures < self._failure_threshold
        return HealthStatus(
            healthy=healthy,
            checked_at=now,
            total_jobs_tracked=total,
            recent_failures=failures,
            last_notification_at=last_notif,
            details={
                "lookback_hours": self._lookback_hours,
                "failure_threshold": self._failure_threshold,
            },
        )
