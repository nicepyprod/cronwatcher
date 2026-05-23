"""Watches the config file for changes and triggers a reload callback."""

import logging
import os
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class ConfigWatcher:
    """Polls the config file mtime and calls `on_change` when it changes."""

    def __init__(
        self,
        config_path: str,
        on_change: Callable[[], None],
        poll_interval: float = 5.0,
    ) -> None:
        self._path = config_path
        self._on_change = on_change
        self._poll_interval = poll_interval
        self._last_mtime: Optional[float] = self._current_mtime()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def _current_mtime(self) -> Optional[float]:
        try:
            return os.path.getmtime(self._path)
        except FileNotFoundError:
            return None

    def _watch_loop(self) -> None:
        while not self._stop_event.is_set():
            mtime = self._current_mtime()
            if mtime != self._last_mtime:
                logger.info("Config file changed, triggering reload: %s", self._path)
                self._last_mtime = mtime
                try:
                    self._on_change()
                except Exception:
                    logger.exception("Error in config reload callback")
            self._stop_event.wait(self._poll_interval)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=self._poll_interval + 1)
