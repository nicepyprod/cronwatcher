"""Rate limiter to suppress duplicate alerts within a cooldown window."""

from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional


@dataclass
class RateLimitEntry:
    job_name: str
    alert_type: str
    last_sent_at: float


class AlertRateLimiter:
    """Prevents sending duplicate alerts for the same job within a cooldown period."""

    def __init__(self, db_path: str = ":memory:", cooldown_seconds: int = 3600) -> None:
        self._db_path = db_path
        self._cooldown = cooldown_seconds
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS alert_rate_limit (
                    job_name TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    last_sent_at REAL NOT NULL,
                    PRIMARY KEY (job_name, alert_type)
                )
                """
            )

    @contextmanager
    def _cursor(self):
        cur = self._conn.cursor()
        try:
            yield cur
            self._conn.commit()
        finally:
            cur.close()

    def is_allowed(self, job_name: str, alert_type: str) -> bool:
        """Return True if an alert should be sent (not within cooldown)."""
        entry = self._get_entry(job_name, alert_type)
        if entry is None:
            return True
        return (time.time() - entry.last_sent_at) >= self._cooldown

    def record_sent(self, job_name: str, alert_type: str) -> None:
        """Record that an alert was sent right now."""
        now = time.time()
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO alert_rate_limit (job_name, alert_type, last_sent_at)
                VALUES (?, ?, ?)
                ON CONFLICT(job_name, alert_type) DO UPDATE SET last_sent_at = excluded.last_sent_at
                """,
                (job_name, alert_type, now),
            )

    def _get_entry(self, job_name: str, alert_type: str) -> Optional[RateLimitEntry]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT job_name, alert_type, last_sent_at FROM alert_rate_limit "
                "WHERE job_name = ? AND alert_type = ?",
                (job_name, alert_type),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return RateLimitEntry(job_name=row[0], alert_type=row[1], last_sent_at=row[2])

    def clear(self, job_name: str, alert_type: str) -> None:
        """Remove rate-limit record so next alert is sent immediately."""
        with self._cursor() as cur:
            cur.execute(
                "DELETE FROM alert_rate_limit WHERE job_name = ? AND alert_type = ?",
                (job_name, alert_type),
            )
