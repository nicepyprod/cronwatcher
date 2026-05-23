"""Tests for the RetentionManager and RetentionPolicy."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from cronwatcher.db import JobRunStore
from cronwatcher.retention import RetentionManager, RetentionPolicy


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def store() -> JobRunStore:
    return JobRunStore(":memory:")


@pytest.fixture()
def policy() -> RetentionPolicy:
    return RetentionPolicy(max_age_days=7, max_runs_per_job=3)


@pytest.fixture()
def manager(store: JobRunStore, policy: RetentionPolicy) -> RetentionManager:
    return RetentionManager(store, policy)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _add_run(
    store: JobRunStore,
    job: str,
    days_ago: float,
    exit_code: int = 0,
) -> None:
    now = datetime.now(tz=timezone.utc)
    started = now - timedelta(days=days_ago)
    run_id = store.start_run(job, started=started)
    store.finish_run(run_id, exit_code, finished=started + timedelta(seconds=1))


# ---------------------------------------------------------------------------
# RetentionPolicy unit tests
# ---------------------------------------------------------------------------


def test_cutoff_is_max_age_days_before_now() -> None:
    policy = RetentionPolicy(max_age_days=10)
    now = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    cutoff = policy.cutoff_time(now=now)
    assert cutoff == datetime(2024, 5, 22, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# RetentionManager.prune — age-based deletion
# ---------------------------------------------------------------------------


def test_prune_removes_old_runs(store: JobRunStore, manager: RetentionManager) -> None:
    _add_run(store, "job_a", days_ago=10)  # older than 7-day window → deleted
    _add_run(store, "job_a", days_ago=2)   # recent → kept

    deleted = manager.prune()

    assert deleted >= 1
    runs = store.get_runs_for_job("job_a")
    assert len(runs) == 1


def test_prune_keeps_recent_runs(store: JobRunStore, manager: RetentionManager) -> None:
    for days in (1, 2, 3):
        _add_run(store, "job_b", days_ago=days)

    deleted = manager.prune()

    assert deleted == 0
    assert len(store.get_runs_for_job("job_b")) == 3


def test_prune_returns_total_deleted(store: JobRunStore, manager: RetentionManager) -> None:
    _add_run(store, "job_c", days_ago=20)
    _add_run(store, "job_c", days_ago=15)
    _add_run(store, "job_c", days_ago=1)

    deleted = manager.prune()

    # 2 old runs removed by age; the 1 recent run kept (no cap exceeded)
    assert deleted == 2


# ---------------------------------------------------------------------------
# RetentionManager.prune — per-job cap
# ---------------------------------------------------------------------------


def test_prune_enforces_max_runs_per_job(store: JobRunStore, manager: RetentionManager) -> None:
    # All runs are recent (within 7 days), but we add 5 — cap is 3
    for i in range(5):
        _add_run(store, "job_d", days_ago=float(i))

    manager.prune()

    remaining = store.get_runs_for_job("job_d")
    assert len(remaining) == 3


def test_prune_no_cap_when_none(store: JobRunStore) -> None:
    policy = RetentionPolicy(max_age_days=30, max_runs_per_job=None)
    mgr = RetentionManager(store, policy)
    for i in range(10):
        _add_run(store, "job_e", days_ago=float(i))

    mgr.prune()

    assert len(store.get_runs_for_job("job_e")) == 10
