"""Tests for RunLockGuard context manager."""

import pytest

from cronwatcher.run_lock import RunLockStore
from cronwatcher.run_lock_guard import RunLockGuard, LockNotAcquiredError


@pytest.fixture
def store() -> RunLockStore:
    return RunLockStore(db_path=":memory:")


@pytest.fixture
def guard(store: RunLockStore) -> RunLockGuard:
    return RunLockGuard(store, ttl_seconds=30)


class TestRunLockGuard:
    def test_lock_acquired_and_released(self, guard: RunLockGuard, store: RunLockStore) -> None:
        with guard.lock("backup"):
            assert store.get_lock("backup") is not None
        assert store.get_lock("backup") is None

    def test_raises_when_already_locked(self, store: RunLockStore) -> None:
        guard_a = RunLockGuard(store, ttl_seconds=30)
        guard_b = RunLockGuard(store, ttl_seconds=30)
        # Override owners to be different so the second acquire truly conflicts
        guard_a._owner = "host-a"
        guard_b._owner = "host-b"

        with guard_a.lock("backup"):
            with pytest.raises(LockNotAcquiredError, match="backup"):
                with guard_b.lock("backup"):
                    pass

    def test_lock_released_on_exception(self, guard: RunLockGuard, store: RunLockStore) -> None:
        with pytest.raises(ValueError):
            with guard.lock("backup"):
                raise ValueError("job failed")
        assert store.get_lock("backup") is None

    def test_is_locked_true_while_held(self, guard: RunLockGuard) -> None:
        with guard.lock("backup"):
            assert guard.is_locked("backup") is True

    def test_is_locked_false_after_release(self, guard: RunLockGuard) -> None:
        with guard.lock("backup"):
            pass
        assert guard.is_locked("backup") is False

    def test_is_locked_false_when_never_acquired(self, guard: RunLockGuard) -> None:
        assert guard.is_locked("never-run") is False
