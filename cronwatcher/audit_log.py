"""Persistent audit log for configuration changes and system events."""

import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, List, Optional


@dataclass
class AuditEntry:
    id: int
    event_type: str
    actor: str
    description: str
    timestamp: float

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "actor": self.actor,
            "description": self.description,
            "timestamp": self.timestamp,
        }


class AuditLog:
    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type  TEXT NOT NULL,
                    actor       TEXT NOT NULL,
                    description TEXT NOT NULL,
                    timestamp   REAL NOT NULL
                )
                """
            )

    @contextmanager
    def _cursor(self) -> Iterator[sqlite3.Cursor]:
        cur = self._conn.cursor()
        try:
            yield cur
            self._conn.commit()
        finally:
            cur.close()

    def record(self, event_type: str, actor: str, description: str, timestamp: Optional[float] = None) -> int:
        ts = timestamp if timestamp is not None else time.time()
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO audit_log (event_type, actor, description, timestamp) VALUES (?, ?, ?, ?)",
                (event_type, actor, description, ts),
            )
            return cur.lastrowid  # type: ignore[return-value]

    def recent(self, limit: int = 50) -> List[AuditEntry]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT id, event_type, actor, description, timestamp FROM audit_log ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            rows = cur.fetchall()
        return [AuditEntry(*row) for row in rows]

    def by_event_type(self, event_type: str) -> List[AuditEntry]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT id, event_type, actor, description, timestamp FROM audit_log WHERE event_type = ? ORDER BY timestamp DESC",
                (event_type,),
            )
            rows = cur.fetchall()
        return [AuditEntry(*row) for row in rows]

    def prune_before(self, cutoff: float) -> int:
        with self._cursor() as cur:
            cur.execute("DELETE FROM audit_log WHERE timestamp < ?", (cutoff,))
            return cur.rowcount
