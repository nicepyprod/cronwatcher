"""Provides a simple SQLite-backed lock to prevent duplicate cron job runs."""

import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional


@dataclass
class LockEntry:
    job_name: str
    acquired_at: float
    expires_at: float
    owner: str


class RunLockStore:
    """SQLite-backed store for distributed-style run locks."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS run_locks (
                    job_name TEXT PRIMARY KEY,
                    acquired_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    owner TEXT NOT NULL
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

    def acquire(self, job_name: str, owner: str, ttl_seconds: float = 300.0) -> bool:
        """Try to acquire a lock. Returns True if acquired, False if already locked."""
        now = time.time()
        expires_at = now + ttl_seconds
        with self._cursor() as cur:
            # Remove expired locks first
            cur.execute(
                "DELETE FROM run_locks WHERE job_name = ? AND expires_at < ?",
                (job_name, now),
            )
            try:
                cur.execute(
                    "INSERT INTO run_locks (job_name, acquired_at, expires_at, owner) VALUES (?, ?, ?, ?)",
                    (job_name, now, expires_at, owner),
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def release(self, job_name: str, owner: str) -> bool:
        """Release a lock held by owner. Returns True if released."""
        with self._cursor() as cur:
            cur.execute(
                "DELETE FROM run_locks WHERE job_name = ? AND owner = ?",
                (job_name, owner),
            )
            return cur.rowcount > 0

    def get_lock(self, job_name: str) -> Optional[LockEntry]:
        """Return the current lock entry if it exists and is not expired."""
        now = time.time()
        with self._cursor() as cur:
            cur.execute(
                "SELECT job_name, acquired_at, expires_at, owner FROM run_locks WHERE job_name = ? AND expires_at >= ?",
                (job_name, now),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return LockEntry(job_name=row[0], acquired_at=row[1], expires_at=row[2], owner=row[3])

    def active_locks(self) -> list[LockEntry]:
        """Return all non-expired lock entries."""
        now = time.time()
        with self._cursor() as cur:
            cur.execute(
                "SELECT job_name, acquired_at, expires_at, owner FROM run_locks WHERE expires_at >= ?",
                (now,),
            )
            rows = cur.fetchall()
        return [LockEntry(job_name=r[0], acquired_at=r[1], expires_at=r[2], owner=r[3]) for r in rows]
