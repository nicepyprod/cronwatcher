"""Job priority levels and priority-aware sorting/filtering."""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable, List


class Priority(IntEnum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

    @classmethod
    def from_string(cls, value: str) -> "Priority":
        mapping = {
            "low": cls.LOW,
            "normal": cls.NORMAL,
            "high": cls.HIGH,
            "critical": cls.CRITICAL,
        }
        normalised = value.strip().lower()
        if normalised not in mapping:
            raise ValueError(
                f"Unknown priority '{value}'. Valid values: {list(mapping)}"
            )
        return mapping[normalised]

    def label(self) -> str:
        return self.name.capitalize()


@dataclass(frozen=True)
class JobPriorityEntry:
    job_name: str
    priority: Priority


class JobPriorityStore:
    """Persists job priority assignments in SQLite."""

    def __init__(self, db_path: str = ":memory:") -> None:
        import sqlite3
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS job_priority (
                    job_name TEXT PRIMARY KEY,
                    priority INTEGER NOT NULL DEFAULT 2
                )
                """
            )

    def set_priority(self, job_name: str, priority: Priority) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO job_priority (job_name, priority)
                VALUES (?, ?)
                ON CONFLICT(job_name) DO UPDATE SET priority = excluded.priority
                """,
                (job_name, int(priority)),
            )

    def get_priority(self, job_name: str) -> Priority:
        cur = self._conn.execute(
            "SELECT priority FROM job_priority WHERE job_name = ?",
            (job_name,),
        )
        row = cur.fetchone()
        return Priority(row[0]) if row else Priority.NORMAL

    def all_entries(self) -> List[JobPriorityEntry]:
        cur = self._conn.execute(
            "SELECT job_name, priority FROM job_priority ORDER BY priority DESC, job_name"
        )
        return [JobPriorityEntry(job_name=r[0], priority=Priority(r[1])) for r in cur.fetchall()]

    def sorted_by_priority(self, job_names: Iterable[str]) -> List[str]:
        """Return job_names sorted highest priority first."""
        def key(name: str) -> int:
            return -int(self.get_priority(name))
        return sorted(job_names, key=key)
