"""Watcher: main daemon loop that polls for missed runs and dispatches alerts."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from cronwatcher.alerts import AlertEvent, AlertSender
from cronwatcher.config import CronWatcherConfig
from cronwatcher.db import JobRunStore
from cronwatcher.scheduler import MissedRunDetector

logger = logging.getLogger(__name__)


class CronWatcher:
    """Daemon that periodically checks for missed cron jobs and sends alerts."""

    def __init__(self, config: CronWatcherConfig, store: JobRunStore) -> None:
        self._config = config
        self._store = store
        self._sender = AlertSender(config.alert)
        self._detector = MissedRunDetector(store, grace_seconds=config.grace_seconds)
        self._running = False

    def _check_once(self) -> None:
        now = datetime.now(tz=timezone.utc)
        missed = self._detector.check_all(self._config.jobs, now)
        for job_name in missed:
            event = AlertEvent(
                job_name=job_name,
                status="missed",
                started_at=now,
                finished_at=now,
                duration=0.0,
                message="Job did not run within the expected window.",
            )
            sent = self._sender.send(event)
            if sent:
                logger.info("Alert sent for missed job '%s'.", job_name)
            else:
                logger.warning("Alert NOT sent for missed job '%s'.", job_name)

    def run_forever(self) -> None:  # pragma: no cover
        """Block and poll at the configured check interval."""
        self._running = True
        logger.info(
            "CronWatcher started. Poll interval: %ds.", self._config.check_interval_seconds
        )
        try:
            while self._running:
                self._check_once()
                time.sleep(self._config.check_interval_seconds)
        except KeyboardInterrupt:
            logger.info("CronWatcher stopped by user.")
        finally:
            self._running = False

    def stop(self) -> None:
        self._running = False
