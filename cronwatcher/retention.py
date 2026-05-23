"""Retention policy: prune old job run records from the database."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Optional

from cronwatcher.db import JobRunStore

logger = logging.getLogger(__name__)


@dataclass
class RetentionPolicy:
    """Defines how long job run history is kept."""

    max_age_days: int = 30
    max_runs_per_job: Optional[int] = 500

    def cutoff_time(self, now: Optional[datetime] = None) -> datetime:
        """Return the earliest timestamp that should be retained."""
        if now is None:
            now = datetime.now(tz=timezone.utc)
        return now - timedelta(days=self.max_age_days)


class RetentionManager:
    """Applies a RetentionPolicy to a JobRunStore, removing stale records."""

    def __init__(self, store: JobRunStore, policy: RetentionPolicy) -> None:
        self._store = store
        self._policy = policy

    def prune(self, now: Optional[datetime] = None) -> int:
        """Delete records older than the policy window.

        Returns the total number of rows deleted.
        """
        cutoff = self._policy.cutoff_time(now)
        deleted = self._store.delete_runs_before(cutoff)
        logger.info(
            "Retention pruned %d run(s) older than %s",
            deleted,
            cutoff.isoformat(),
        )
        if self._policy.max_runs_per_job is not None:
            extra = self._store.delete_excess_runs_per_job(
                self._policy.max_runs_per_job
            )
            deleted += extra
            logger.info(
                "Retention pruned %d excess run(s) (cap=%d per job)",
                extra,
                self._policy.max_runs_per_job,
            )
        return deleted
