"""Track inter-job dependencies and detect dependency violations."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class DependencyViolation:
    job_name: str
    depends_on: str
    reason: str

    def __str__(self) -> str:
        return f"{self.job_name} depends on {self.depends_on}: {self.reason}"


class JobDependencyStore:
    """Persist and query job dependency edges in SQLite."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS job_dependencies (
                    job_name   TEXT NOT NULL,
                    depends_on TEXT NOT NULL,
                    PRIMARY KEY (job_name, depends_on)
                )
                """
            )

    @contextmanager
    def _cursor(self):
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            yield cur
            conn.commit()
        finally:
            conn.close()

    def add_dependency(self, job_name: str, depends_on: str) -> None:
        """Record that *job_name* must run after *depends_on* succeeds."""
        with self._cursor() as cur:
            cur.execute(
                "INSERT OR IGNORE INTO job_dependencies (job_name, depends_on) VALUES (?, ?)",
                (job_name, depends_on),
            )

    def remove_dependency(self, job_name: str, depends_on: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "DELETE FROM job_dependencies WHERE job_name = ? AND depends_on = ?",
                (job_name, depends_on),
            )

    def get_dependencies(self, job_name: str) -> List[str]:
        """Return list of job names that *job_name* depends on."""
        with self._cursor() as cur:
            rows = cur.execute(
                "SELECT depends_on FROM job_dependencies WHERE job_name = ?",
                (job_name,),
            ).fetchall()
        return [r["depends_on"] for r in rows]

    def get_dependents(self, job_name: str) -> List[str]:
        """Return jobs that depend on *job_name*."""
        with self._cursor() as cur:
            rows = cur.execute(
                "SELECT job_name FROM job_dependencies WHERE depends_on = ?",
                (job_name,),
            ).fetchall()
        return [r["job_name"] for r in rows]

    def all_dependencies(self) -> Dict[str, List[str]]:
        """Return mapping of job_name -> [depends_on, ...] for all edges."""
        with self._cursor() as cur:
            rows = cur.execute(
                "SELECT job_name, depends_on FROM job_dependencies ORDER BY job_name"
            ).fetchall()
        result: Dict[str, List[str]] = {}
        for row in rows:
            result.setdefault(row["job_name"], []).append(row["depends_on"])
        return result
