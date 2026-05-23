"""Schedule and trigger periodic digest emails."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime

from cronwatcher.digest import DigestSender

logger = logging.getLogger(__name__)


class DigestScheduler:
    """Runs DigestSender on a fixed interval (default every 24 h).

    Designed to be executed in a background daemon thread alongside the
    main CronWatcher loop.
    """

    def __init__(
        self,
        sender: DigestSender,
        interval_seconds: int = 86_400,
        tick_seconds: int = 60,
    ) -> None:
        self._sender = sender
        self._interval = interval_seconds
        self._tick = tick_seconds
        self._stop_event = threading.Event()
        self._last_sent: datetime | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_forever(self) -> None:  # pragma: no cover
        """Block indefinitely, sending digests at *interval_seconds* cadence."""
        logger.info(
            "DigestScheduler started (interval=%ds, tick=%ds).",
            self._interval,
            self._tick,
        )
        while not self._stop_event.is_set():
            self._maybe_send()
            self._stop_event.wait(self._tick)
        logger.info("DigestScheduler stopped.")

    def stop(self) -> None:
        self._stop_event.set()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _maybe_send(self) -> None:
        now = datetime.utcnow()
        if self._last_sent is None or (now - self._last_sent).total_seconds() >= self._interval:
            logger.debug("Triggering digest at %s.", now.isoformat())
            ok = self._sender.send(now=now)
            if ok:
                self._last_sent = now
