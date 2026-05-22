"""SQLite-backed storage for cron job execution records."""

import sqlite3
import contextlib
from datetime import datetime
from typing import Optional, List, Tuple


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS job_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_name    TEXT NOT NULL,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    duration_s  REAL,
    exit_code   INTEGER,
    status      TEXT NOT NULL DEFAULT 'running'
);
"""


class JobRunStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    @contextlib.contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        with self._conn() as conn:
            conn.execute(CREATE_TABLE_SQL)

    def start_run(self, job_name: str, started_at: Optional[datetime] = None) -> int:
        started_at = started_at or datetime.utcnow()
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO job_runs (job_name, started_at, status) VALUES (?, ?, 'running')",
                (job_name, started_at.isoformat()),
            )
            return cur.lastrowid

    def finish_run(self, run_id: int, exit_code: int, finished_at: Optional[datetime] = None):
        finished_at = finished_at or datetime.utcnow()
        status = "success" if exit_code == 0 else "failure"
        with self._conn() as conn:
            conn.execute(
                """UPDATE job_runs
                   SET finished_at = ?, exit_code = ?,
                       duration_s = (julianday(?) - julianday(started_at)) * 86400,
                       status = ?
                   WHERE id = ?""",
                (finished_at.isoformat(), exit_code, finished_at.isoformat(), status, run_id),
            )

    def get_last_run(self, job_name: str) -> Optional[sqlite3.Row]:
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT * FROM job_runs WHERE job_name = ? ORDER BY started_at DESC LIMIT 1",
                (job_name,),
            )
            return cur.fetchone()

    def get_runs(self, job_name: str, limit: int = 20) -> List[sqlite3.Row]:
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT * FROM job_runs WHERE job_name = ? ORDER BY started_at DESC LIMIT ?",
                (job_name, limit),
            )
            return cur.fetchall()
