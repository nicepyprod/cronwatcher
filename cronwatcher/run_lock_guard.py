"""Context manager that acquires and releases a RunLock around a job execution."""

import socket
from contextlib import contextmanager
from typing import Generator

from cronwatcher.run_lock import RunLockStore


class LockNotAcquiredError(Exception):
    """Raised when a run lock cannot be acquired."""


class RunLockGuard:
    """Wraps RunLockStore to provide a context-manager interface for job locking."""

    def __init__(self, store: RunLockStore, ttl_seconds: float = 300.0) -> None:
        self._store = store
        self._ttl = ttl_seconds
        self._owner = socket.gethostname()

    @contextmanager
    def lock(self, job_name: str) -> Generator[None, None, None]:
        """Acquire lock before yielding; release on exit. Raises if lock unavailable."""
        acquired = self._store.acquire(job_name, owner=self._owner, ttl_seconds=self._ttl)
        if not acquired:
            entry = self._store.get_lock(job_name)
            owner_info = entry.owner if entry else "unknown"
            raise LockNotAcquiredError(
                f"Job '{job_name}' is already locked by '{owner_info}'."
            )
        try:
            yield
        finally:
            self._store.release(job_name, owner=self._owner)

    def is_locked(self, job_name: str) -> bool:
        """Return True if the job currently holds an active lock."""
        return self._store.get_lock(job_name) is not None
