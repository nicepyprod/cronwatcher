"""Scheduler: detects missed cron runs by comparing last execution time to expected schedule."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from croniter import croniter

from cronwatcher.config import JobConfig
from cronwatcher.db import JobRunStore

logger = logging.getLogger(__name__)


class MissedRunDetector:
    """Checks whether a cron job has missed its expected execution window."""

    def __init__(self, store: JobRunStore, grace_seconds: int = 60) -> None:
        self._store = store
        self._grace_seconds = grace_seconds

    def last_expected_run(self, job: JobConfig, now: Optional[datetime] = None) -> datetime:
        """Return the most recent scheduled time before *now* for the given job."""
        if now is None:
            now = datetime.now(tz=timezone.utc)
        cron = croniter(job.schedule, now)
        return cron.get_prev(datetime)

    def is_missed(self, job: JobConfig, now: Optional[datetime] = None) -> bool:
        """Return True if the job missed its last expected run."""
        if now is None:
            now = datetime.now(tz=timezone.utc)

        expected = self.last_expected_run(job, now)
        deadline = expected.timestamp() + self._grace_seconds

        last_run = self._store.last_run(job.name)
        if last_run is None:
            logger.warning("Job '%s' has no recorded runs; treating as missed.", job.name)
            return now.timestamp() > deadline

        last_start_ts = last_run["started_at"]
        return last_start_ts < expected.timestamp() and now.timestamp() > deadline

    def check_all(self, jobs: list[JobConfig], now: Optional[datetime] = None) -> list[str]:
        """Return names of all jobs that appear to have missed their last run."""
        missed = []
        for job in jobs:
            try:
                if self.is_missed(job, now):
                    missed.append(job.name)
                    logger.info("Missed run detected for job '%s'.", job.name)
            except Exception as exc:  # pragma: no cover
                logger.error("Error checking job '%s': %s", job.name, exc)
        return missed
