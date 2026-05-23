"""SQLite-backed store for cron job run records."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, List, Optional


class JobRunStore:
    def __init__(self, db_path: str = ":memory:"):
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS job_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_name TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT,
                duration_seconds REAL,
                exit_code INTEGER
            )
            """
        )
        self._conn.commit()

    def start_run(self, job_name: str) -> int:
        cur = self._conn.execute(
            "INSERT INTO job_runs (job_name, started_at, status) VALUES (?, ?, ?)",
            (job_name, datetime.utcnow().isoformat(), "running"),
        )
        self._conn.commit()
        return cur.lastrowid

    def finish_run(self, run_id: int, status: str, exit_code: int = 0) -> None:
        finished_at = datetime.utcnow().isoformat()
        self._conn.execute(
            """
            UPDATE job_runs
            SET finished_at = ?,
                status = ?,
                exit_code = ?,
                duration_seconds = (
                    julianday(?) - julianday(started_at)
                ) * 86400
            WHERE id = ?
            """,
            (finished_at, status, exit_code, finished_at, run_id),
        )
        self._conn.commit()

    def get_last_run(self, job_name: str) -> Optional[Dict]:
        row = self._conn.execute(
            "SELECT * FROM job_runs WHERE job_name = ? ORDER BY started_at DESC LIMIT 1",
            (job_name,),
        ).fetchone()
        return dict(row) if row else None

    def get_runs_since(self, job_name: str, since: datetime) -> List[Dict]:
        rows = self._conn.execute(
            """
            SELECT * FROM job_runs
            WHERE job_name = ? AND started_at >= ?
            ORDER BY started_at ASC
            """,
            (job_name, since.isoformat()),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_running_jobs(self) -> List[Dict]:
        rows = self._conn.execute(
            "SELECT * FROM job_runs WHERE status = 'running'"
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self._conn.close()
