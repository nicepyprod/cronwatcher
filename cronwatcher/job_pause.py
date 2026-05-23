"""Pause and resume cron jobs, preventing alerts and missed-run detection."""

from __future__ import annotations

import sqlite3
import contextlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator, List, Optional


@dataclass
class PauseEntry:
    job_name: str
    paused_at: datetime
    reason: Optional[str]
    paused_until: Optional[datetime]

    def is_active(self, now: Optional[datetime] = None) -> bool:
        """Return True if the pause is still in effect."""
        if now is None:
            now = datetime.now(timezone.utc)
        if self.paused_until is None:
            return True
        return now < self.paused_until


class JobPauseStore:
    """Persist and query job pause state using SQLite."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS job_pauses (
                    job_name     TEXT PRIMARY KEY,
                    paused_at    TEXT NOT NULL,
                    reason       TEXT,
                    paused_until TEXT
                )
                """
            )

    @contextlib.contextmanager
    def _cursor(self) -> Iterator[sqlite3.Cursor]:
        conn = sqlite3.connect(self._db_path)
        try:
            cur = conn.cursor()
            yield cur
            conn.commit()
        finally:
            conn.close()

    def pause(self, job_name: str, reason: Optional[str] = None,
              paused_until: Optional[datetime] = None) -> PauseEntry:
        now = datetime.now(timezone.utc)
        until_str = paused_until.isoformat() if paused_until else None
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO job_pauses (job_name, paused_at, reason, paused_until)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(job_name) DO UPDATE SET
                    paused_at = excluded.paused_at,
                    reason = excluded.reason,
                    paused_until = excluded.paused_until
                """,
                (job_name, now.isoformat(), reason, until_str),
            )
        return PauseEntry(job_name=job_name, paused_at=now,
                          reason=reason, paused_until=paused_until)

    def resume(self, job_name: str) -> bool:
        with self._cursor() as cur:
            cur.execute("DELETE FROM job_pauses WHERE job_name = ?", (job_name,))
            return cur.rowcount > 0

    def get(self, job_name: str) -> Optional[PauseEntry]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT job_name, paused_at, reason, paused_until "
                "FROM job_pauses WHERE job_name = ?",
                (job_name,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_entry(row)

    def is_paused(self, job_name: str,
                  now: Optional[datetime] = None) -> bool:
        entry = self.get(job_name)
        if entry is None:
            return False
        return entry.is_active(now)

    def all_paused(self) -> List[PauseEntry]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT job_name, paused_at, reason, paused_until FROM job_pauses"
            )
            rows = cur.fetchall()
        return [self._row_to_entry(r) for r in rows]

    @staticmethod
    def _row_to_entry(row: tuple) -> PauseEntry:
        job_name, paused_at_str, reason, until_str = row
        return PauseEntry(
            job_name=job_name,
            paused_at=datetime.fromisoformat(paused_at_str),
            reason=reason,
            paused_until=datetime.fromisoformat(until_str) if until_str else None,
        )
