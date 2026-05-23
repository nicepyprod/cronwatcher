"""Tagging support for cron jobs — assign and query string tags."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Generator, List


class JobTags:
    """Persistent store for job tags backed by SQLite."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS job_tags (
                    job_name TEXT NOT NULL,
                    tag      TEXT NOT NULL,
                    PRIMARY KEY (job_name, tag)
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

    def add_tag(self, job_name: str, tag: str) -> None:
        """Add a tag to a job (idempotent)."""
        tag = tag.strip().lower()
        if not tag:
            raise ValueError("tag must not be empty")
        with self._cursor() as cur:
            cur.execute(
                "INSERT OR IGNORE INTO job_tags (job_name, tag) VALUES (?, ?)",
                (job_name, tag),
            )

    def remove_tag(self, job_name: str, tag: str) -> None:
        """Remove a tag from a job."""
        with self._cursor() as cur:
            cur.execute(
                "DELETE FROM job_tags WHERE job_name = ? AND tag = ?",
                (job_name, tag.strip().lower()),
            )

    def get_tags(self, job_name: str) -> List[str]:
        """Return all tags for a job, sorted alphabetically."""
        with self._cursor() as cur:
            rows = cur.execute(
                "SELECT tag FROM job_tags WHERE job_name = ? ORDER BY tag",
                (job_name,),
            ).fetchall()
        return [r[0] for r in rows]

    def jobs_with_tag(self, tag: str) -> List[str]:
        """Return all job names that carry the given tag."""
        with self._cursor() as cur:
            rows = cur.execute(
                "SELECT job_name FROM job_tags WHERE tag = ? ORDER BY job_name",
                (tag.strip().lower(),),
            ).fetchall()
        return [r[0] for r in rows]

    def clear_tags(self, job_name: str) -> None:
        """Remove all tags from a job."""
        with self._cursor() as cur:
            cur.execute("DELETE FROM job_tags WHERE job_name = ?", (job_name,))
