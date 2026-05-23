"""Tests for JobRunStore (including new retention helpers)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from cronwatcher.db import JobRunStore


@pytest.fixture()
def store() -> JobRunStore:
    return JobRunStore(":memory:")


# ---------------------------------------------------------------------------
# Basic run lifecycle
# ---------------------------------------------------------------------------


def test_start_and_finish_run_success(store: JobRunStore) -> None:
    run_id = store.start_run("backup")
    store.finish_run(run_id, exit_code=0)
    row = store.get_run(run_id)
    assert row is not None
    assert row["success"] == 1
    assert row["exit_code"] == 0


def test_start_and_finish_run_failure(store: JobRunStore) -> None:
    run_id = store.start_run("backup")
    store.finish_run(run_id, exit_code=1)
    row = store.get_run(run_id)
    assert row["success"] == 0


def test_running_status_before_finish(store: JobRunStore) -> None:
    run_id = store.start_run("sync")
    row = store.get_run(run_id)
    assert row["finished"] is None
    assert row["exit_code"] is None


def test_duration_is_positive(store: JobRunStore) -> None:
    now = datetime.now(tz=timezone.utc)
    started = now - timedelta(seconds=5)
    run_id = store.start_run("cleanup", started=started)
    store.finish_run(run_id, exit_code=0, finished=now)
    row = store.get_run(run_id)
    start_dt = datetime.fromisoformat(row["started"])
    end_dt = datetime.fromisoformat(row["finished"])
    assert (end_dt - start_dt).total_seconds() > 0


def test_get_last_run_returns_most_recent(store: JobRunStore) -> None:
    now = datetime.now(tz=timezone.utc)
    id1 = store.start_run("job", started=now - timedelta(hours=2))
    store.finish_run(id1, 0)
    id2 = store.start_run("job", started=now - timedelta(hours=1))
    store.finish_run(id2, 0)
    last = store.get_last_run("job")
    assert last is not None
    assert last["id"] == id2


def test_all_job_names(store: JobRunStore) -> None:
    store.start_run("alpha")
    store.start_run("beta")
    store.start_run("alpha")
    names = store.all_job_names()
    assert set(names) == {"alpha", "beta"}


# ---------------------------------------------------------------------------
# Retention helpers
# ---------------------------------------------------------------------------


def test_delete_runs_before_cutoff(store: JobRunStore) -> None:
    now = datetime.now(tz=timezone.utc)
    old = now - timedelta(days=10)
    recent = now - timedelta(days=1)
    old_id = store.start_run("j", started=old)
    store.finish_run(old_id, 0)
    new_id = store.start_run("j", started=recent)
    store.finish_run(new_id, 0)

    deleted = store.delete_runs_before(now - timedelta(days=5))

    assert deleted == 1
    assert store.get_run(old_id) is None
    assert store.get_run(new_id) is not None


def test_delete_excess_runs_per_job_keeps_newest(store: JobRunStore) -> None:
    now = datetime.now(tz=timezone.utc)
    ids = []
    for i in range(5):
        rid = store.start_run("j", started=now - timedelta(hours=5 - i))
        store.finish_run(rid, 0)
        ids.append(rid)

    store.delete_excess_runs_per_job(max_runs=3)

    remaining = store.get_runs_for_job("j")
    assert len(remaining) == 3
    remaining_ids = {r["id"] for r in remaining}
    # The 3 most-recent runs should survive
    assert ids[-1] in remaining_ids
    assert ids[-2] in remaining_ids
    assert ids[-3] in remaining_ids
