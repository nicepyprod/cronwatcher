"""Persistent log of sent notifications backed by SQLite."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import List, Optional


class NotificationLogEntry:
    __slots__ = ("id", "job_name", "severity", "sent_at", "success", "error")

    def __init__(self, id: Optional[int], job_name: str, severity: str,
                 sent_at: datetime, success: bool, error: str):
        self.id = id
        self.job_name = job_name
        self.severity = severity
        self.sent_at = sent_at
        self.success = success
        self.error = error


class NotificationLog:
    """Stores notification history in SQLite."""

    def __init__(self, db_path: str = ":memory:"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notification_log (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                job_name TEXT    NOT NULL,
                severity TEXT    NOT NULL,
                sent_at  TEXT    NOT NULL,
                success  INTEGER NOT NULL DEFAULT 1,
                error    TEXT    NOT NULL DEFAULT ''
            )
            """
        )
        self._conn.commit()

    def record(self, job_name: str, severity: str, success: bool, error: str = "") -> int:
        cur = self._conn.execute(
            "INSERT INTO notification_log (job_name, severity, sent_at, success, error) "
            "VALUES (?, ?, ?, ?, ?)",
            (job_name, severity, datetime.utcnow().isoformat(), int(success), error),
        )
        self._conn.commit()
        return cur.lastrowid

    def recent(self, job_name: str, limit: int = 10) -> List[NotificationLogEntry]:
        cur = self._conn.execute(
            "SELECT id, job_name, severity, sent_at, success, error "
            "FROM notification_log WHERE job_name = ? ORDER BY sent_at DESC LIMIT ?",
            (job_name, limit),
        )
        rows = cur.fetchall()
        return [
            NotificationLogEntry(
                id=r[0], job_name=r[1], severity=r[2],
                sent_at=datetime.fromisoformat(r[3]), success=bool(r[4]), error=r[5]
            )
            for r in rows
        ]

    def close(self) -> None:
        self._conn.close()
