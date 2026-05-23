"""Per-job run quota enforcement: limit how many times a job may run within a time window."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterator, Optional


@dataclass
class QuotaViolation:
    job_name: str
    window_seconds: int
    max_runs: int
    actual_runs: int

    def __str__(self) -> str:
        return (
            f"Job '{self.job_name}' exceeded quota: "
            f"{self.actual_runs}/{self.max_runs} runs "
            f"in the last {self.window_seconds}s"
        )


@dataclass
class QuotaEntry:
    job_name: str
    max_runs: int
    window_seconds: int


class JobQuotaStore:
    """Stores per-job quota definitions and checks run counts against them."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS job_quotas (
                    job_name TEXT PRIMARY KEY,
                    max_runs INTEGER NOT NULL,
                    window_seconds INTEGER NOT NULL
                )
                """
            )

    @contextmanager
    def _cursor(self) -> Iterator[sqlite3.Cursor]:
        conn = sqlite3.connect(self._db_path)
        try:
            cur = conn.cursor()
            yield cur
            conn.commit()
        finally:
            conn.close()

    def set_quota(self, job_name: str, max_runs: int, window_seconds: int) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO job_quotas (job_name, max_runs, window_seconds)
                VALUES (?, ?, ?)
                ON CONFLICT(job_name) DO UPDATE SET
                    max_runs=excluded.max_runs,
                    window_seconds=excluded.window_seconds
                """,
                (job_name, max_runs, window_seconds),
            )

    def get_quota(self, job_name: str) -> Optional[QuotaEntry]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT job_name, max_runs, window_seconds FROM job_quotas WHERE job_name=?",
                (job_name,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return QuotaEntry(job_name=row[0], max_runs=row[1], window_seconds=row[2])

    def remove_quota(self, job_name: str) -> None:
        with self._cursor() as cur:
            cur.execute("DELETE FROM job_quotas WHERE job_name=?", (job_name,))

    def all_quotas(self) -> list[QuotaEntry]:
        with self._cursor() as cur:
            cur.execute("SELECT job_name, max_runs, window_seconds FROM job_quotas")
            rows = cur.fetchall()
        return [QuotaEntry(job_name=r[0], max_runs=r[1], window_seconds=r[2]) for r in rows]
