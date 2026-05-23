"""Tagging/labelling support for cron jobs.

Allows jobs to be annotated with arbitrary string labels (e.g. team, env,
criticality) so that reports and alerts can be filtered or grouped by label.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Dict, Generator, List, Optional


class JobLabels:
    """Stores and retrieves key/value labels associated with job names."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS job_labels (
                    job_name TEXT NOT NULL,
                    key      TEXT NOT NULL,
                    value    TEXT NOT NULL,
                    PRIMARY KEY (job_name, key)
                )
                """
            )

    @contextmanager
    def _cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            yield cur
            conn.commit()
        finally:
            conn.close()

    def set_label(self, job_name: str, key: str, value: str) -> None:
        """Insert or replace a label for *job_name*."""
        with self._cursor() as cur:
            cur.execute(
                "INSERT OR REPLACE INTO job_labels (job_name, key, value) VALUES (?, ?, ?)",
                (job_name, key, value),
            )

    def remove_label(self, job_name: str, key: str) -> None:
        """Delete a specific label key from *job_name*."""
        with self._cursor() as cur:
            cur.execute(
                "DELETE FROM job_labels WHERE job_name = ? AND key = ?",
                (job_name, key),
            )

    def get_labels(self, job_name: str) -> Dict[str, str]:
        """Return all labels for *job_name* as a plain dict."""
        with self._cursor() as cur:
            rows = cur.execute(
                "SELECT key, value FROM job_labels WHERE job_name = ?",
                (job_name,),
            ).fetchall()
        return {row["key"]: row["value"] for row in rows}

    def jobs_with_label(self, key: str, value: Optional[str] = None) -> List[str]:
        """Return job names that have *key* (optionally matching *value*)."""
        with self._cursor() as cur:
            if value is None:
                rows = cur.execute(
                    "SELECT DISTINCT job_name FROM job_labels WHERE key = ?",
                    (key,),
                ).fetchall()
            else:
                rows = cur.execute(
                    "SELECT DISTINCT job_name FROM job_labels WHERE key = ? AND value = ?",
                    (key, value),
                ).fetchall()
        return [row["job_name"] for row in rows]

    def clear_job(self, job_name: str) -> None:
        """Remove all labels for *job_name*."""
        with self._cursor() as cur:
            cur.execute("DELETE FROM job_labels WHERE job_name = ?", (job_name,))
