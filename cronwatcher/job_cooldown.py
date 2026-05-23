"""Enforce minimum time between successive runs of the same job."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional


@dataclass
class CooldownViolation:
    job_name: str
    last_run_at: datetime
    cooldown_seconds: int
    earliest_next_run: datetime

    def __str__(self) -> str:
        return (
            f"Job '{self.job_name}' is in cooldown until "
            f"{self.earliest_next_run.isoformat()} "
            f"(last ran at {self.last_run_at.isoformat()})"
        )


class JobCooldownStore:
    """Persist per-job cooldown settings (minimum seconds between runs)."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS job_cooldowns (
                    job_name TEXT PRIMARY KEY,
                    cooldown_seconds INTEGER NOT NULL
                )
                """
            )

    @contextmanager
    def _cursor(self):
        conn = sqlite3.connect(self._db_path)
        try:
            cur = conn.cursor()
            yield cur
            conn.commit()
        finally:
            conn.close()

    def set_cooldown(self, job_name: str, cooldown_seconds: int) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO job_cooldowns (job_name, cooldown_seconds)
                VALUES (?, ?)
                ON CONFLICT(job_name) DO UPDATE SET cooldown_seconds = excluded.cooldown_seconds
                """,
                (job_name, cooldown_seconds),
            )

    def get_cooldown(self, job_name: str) -> Optional[int]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT cooldown_seconds FROM job_cooldowns WHERE job_name = ?",
                (job_name,),
            )
            row = cur.fetchone()
        return row[0] if row else None

    def remove_cooldown(self, job_name: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "DELETE FROM job_cooldowns WHERE job_name = ?", (job_name,)
            )


class CooldownChecker:
    """Check whether a job is still within its cooldown period."""

    def __init__(self, cooldown_store: JobCooldownStore) -> None:
        self._store = cooldown_store

    def check(
        self, job_name: str, last_run_at: Optional[datetime]
    ) -> Optional[CooldownViolation]:
        cooldown_seconds = self._store.get_cooldown(job_name)
        if cooldown_seconds is None or last_run_at is None:
            return None

        now = datetime.now(tz=timezone.utc)
        elapsed = (now - last_run_at).total_seconds()
        if elapsed >= cooldown_seconds:
            return None

        earliest_next = last_run_at + timedelta(seconds=cooldown_seconds)
        return CooldownViolation(
            job_name=job_name,
            last_run_at=last_run_at,
            cooldown_seconds=cooldown_seconds,
            earliest_next_run=earliest_next,
        )

    def is_in_cooldown(
        self, job_name: str, last_run_at: Optional[datetime]
    ) -> bool:
        return self.check(job_name, last_run_at) is not None
