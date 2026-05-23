"""Persistent store for job run records (SQLite-backed)."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, List, Optional, Tuple


class JobRunStore:
    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS job_runs (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_name  TEXT    NOT NULL,
                    started   TEXT    NOT NULL,
                    finished  TEXT,
                    exit_code INTEGER,
                    success   INTEGER
                )
                """
            )

    @contextmanager
    def _cursor(self) -> Iterator[sqlite3.Cursor]:
        cur = self._conn.cursor()
        try:
            yield cur
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        finally:
            cur.close()

    # ------------------------------------------------------------------
    # Write helpers
    # ------------------------------------------------------------------

    def start_run(self, job_name: str, started: Optional[datetime] = None) -> int:
        if started is None:
            started = datetime.now(tz=timezone.utc)
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO job_runs (job_name, started) VALUES (?, ?)",
                (job_name, started.isoformat()),
            )
            return cur.lastrowid  # type: ignore[return-value]

    def finish_run(
        self,
        run_id: int,
        exit_code: int,
        finished: Optional[datetime] = None,
    ) -> None:
        if finished is None:
            finished = datetime.now(tz=timezone.utc)
        success = 1 if exit_code == 0 else 0
        with self._cursor() as cur:
            cur.execute(
                """
                UPDATE job_runs
                SET finished=?, exit_code=?, success=?
                WHERE id=?
                """,
                (finished.isoformat(), exit_code, success, run_id),
            )

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def get_run(self, run_id: int) -> Optional[sqlite3.Row]:
        self._conn.row_factory = sqlite3.Row
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM job_runs WHERE id=?", (run_id,))
        return cur.fetchone()

    def get_runs_for_job(
        self, job_name: str, limit: int = 100
    ) -> List[sqlite3.Row]:
        self._conn.row_factory = sqlite3.Row
        cur = self._conn.cursor()
        cur.execute(
            "SELECT * FROM job_runs WHERE job_name=? ORDER BY started DESC LIMIT ?",
            (job_name, limit),
        )
        return cur.fetchall()

    def get_last_run(self, job_name: str) -> Optional[sqlite3.Row]:
        rows = self.get_runs_for_job(job_name, limit=1)
        return rows[0] if rows else None

    def all_job_names(self) -> List[str]:
        cur = self._conn.cursor()
        cur.execute("SELECT DISTINCT job_name FROM job_runs")
        return [r[0] for r in cur.fetchall()]

    def get_all_runs(self) -> List[sqlite3.Row]:
        self._conn.row_factory = sqlite3.Row
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM job_runs ORDER BY started DESC")
        return cur.fetchall()

    # ------------------------------------------------------------------
    # Retention helpers
    # ------------------------------------------------------------------

    def delete_runs_before(self, cutoff: datetime) -> int:
        """Delete all runs whose *started* timestamp is before *cutoff*."""
        with self._cursor() as cur:
            cur.execute(
                "DELETE FROM job_runs WHERE started < ?",
                (cutoff.isoformat(),),
            )
            return cur.rowcount

    def delete_excess_runs_per_job(self, max_runs: int) -> int:
        """Keep only the *max_runs* most-recent runs per job; delete the rest."""
        job_names = self.all_job_names()
        total_deleted = 0
        for name in job_names:
            with self._cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM job_runs
                    WHERE job_name = ?
                      AND id NOT IN (
                          SELECT id FROM job_runs
                          WHERE job_name = ?
                          ORDER BY started DESC
                          LIMIT ?
                      )
                    """,
                    (name, name, max_runs),
                )
                total_deleted += cur.rowcount
        return total_deleted
