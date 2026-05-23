"""Per-job free-form annotation storage backed by SQLite."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Generator, Optional


@dataclass
class Annotation:
    job_name: str
    key: str
    value: str
    updated_at: datetime


class JobAnnotations:
    """Store and retrieve string annotations (key/value pairs) for cron jobs."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS job_annotations (
                    job_name  TEXT NOT NULL,
                    key       TEXT NOT NULL,
                    value     TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (job_name, key)
                )
                """
            )

    @contextmanager
    def _cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        conn = sqlite3.connect(self._db_path)
        try:
            cur = conn.cursor()
            yield cur
            conn.commit()
        finally:
            conn.close()

    def set_annotation(self, job_name: str, key: str, value: str) -> None:
        """Insert or replace an annotation for *job_name*."""
        now = datetime.now(timezone.utc).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO job_annotations (job_name, key, value, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(job_name, key) DO UPDATE SET value=excluded.value,
                    updated_at=excluded.updated_at
                """,
                (job_name, key, value, now),
            )

    def get_annotation(self, job_name: str, key: str) -> Optional[str]:
        """Return the value for *key* on *job_name*, or *None* if absent."""
        with self._cursor() as cur:
            row = cur.execute(
                "SELECT value FROM job_annotations WHERE job_name=? AND key=?",
                (job_name, key),
            ).fetchone()
        return row[0] if row else None

    def get_all(self, job_name: str) -> dict[str, str]:
        """Return all annotations for *job_name* as a plain dict."""
        with self._cursor() as cur:
            rows = cur.execute(
                "SELECT key, value FROM job_annotations WHERE job_name=? ORDER BY key",
                (job_name,),
            ).fetchall()
        return {k: v for k, v in rows}

    def delete_annotation(self, job_name: str, key: str) -> bool:
        """Remove a single annotation. Returns *True* if a row was deleted."""
        with self._cursor() as cur:
            cur.execute(
                "DELETE FROM job_annotations WHERE job_name=? AND key=?",
                (job_name, key),
            )
            deleted = cur.rowcount > 0
        return deleted

    def delete_all(self, job_name: str) -> int:
        """Remove all annotations for *job_name*. Returns the number of rows deleted."""
        with self._cursor() as cur:
            cur.execute(
                "DELETE FROM job_annotations WHERE job_name=?",
                (job_name,),
            )
            count = cur.rowcount
        return count
