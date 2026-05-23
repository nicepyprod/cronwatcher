"""Tests for RunLockStore."""

import time

import pytest

from cronwatcher.run_lock import RunLockStore, LockEntry


@pytest.fixture
def store() -> RunLockStore:
    return RunLockStore(db_path=":memory:")


class TestAcquire:
    def test_first_acquire_succeeds(self, store: RunLockStore) -> None:
        assert store.acquire("backup", owner="host-a") is True

    def test_second_acquire_fails_while_locked(self, store: RunLockStore) -> None:
        store.acquire("backup", owner="host-a")
        assert store.acquire("backup", owner="host-b") is False

    def test_different_jobs_do_not_conflict(self, store: RunLockStore) -> None:
        assert store.acquire("job-a", owner="host-a") is True
        assert store.acquire("job-b", owner="host-a") is True

    def test_expired_lock_can_be_reacquired(self, store: RunLockStore) -> None:
        store.acquire("backup", owner="host-a", ttl_seconds=0.01)
        time.sleep(0.05)
        assert store.acquire("backup", owner="host-b") is True


class TestRelease:
    def test_release_allows_reacquire(self, store: RunLockStore) -> None:
        store.acquire("backup", owner="host-a")
        store.release("backup", owner="host-a")
        assert store.acquire("backup", owner="host-b") is True

    def test_release_by_wrong_owner_fails(self, store: RunLockStore) -> None:
        store.acquire("backup", owner="host-a")
        released = store.release("backup", owner="host-b")
        assert released is False
        assert store.get_lock("backup") is not None

    def test_release_nonexistent_lock_returns_false(self, store: RunLockStore) -> None:
        assert store.release("nonexistent", owner="host-a") is False


class TestGetLock:
    def test_returns_none_when_no_lock(self, store: RunLockStore) -> None:
        assert store.get_lock("backup") is None

    def test_returns_entry_when_locked(self, store: RunLockStore) -> None:
        store.acquire("backup", owner="host-a", ttl_seconds=60)
        entry = store.get_lock("backup")
        assert isinstance(entry, LockEntry)
        assert entry.job_name == "backup"
        assert entry.owner == "host-a"

    def test_returns_none_after_expiry(self, store: RunLockStore) -> None:
        store.acquire("backup", owner="host-a", ttl_seconds=0.01)
        time.sleep(0.05)
        assert store.get_lock("backup") is None


class TestActiveLocks:
    def test_empty_when_no_locks(self, store: RunLockStore) -> None:
        assert store.active_locks() == []

    def test_returns_all_active_locks(self, store: RunLockStore) -> None:
        store.acquire("job-a", owner="host-a")
        store.acquire("job-b", owner="host-b")
        locks = store.active_locks()
        names = {lock.job_name for lock in locks}
        assert names == {"job-a", "job-b"}

    def test_excludes_expired_locks(self, store: RunLockStore) -> None:
        store.acquire("job-a", owner="host-a", ttl_seconds=0.01)
        store.acquire("job-b", owner="host-b", ttl_seconds=60)
        time.sleep(0.05)
        # Trigger expiry cleanup by attempting acquire
        store.acquire("job-a", owner="host-c")
        locks = store.active_locks()
        names = {lock.job_name for lock in locks}
        assert "job-b" in names
