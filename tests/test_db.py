"""Tests for cronwatcher job run storage."""

import os
import tempfile
from datetime import datetime, timedelta

import pytest

from cronwatcher.db import JobRunStore


@pytest.fixture
def store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = JobRunStore(path)
    yield s
    os.unlink(path)


def test_start_and_finish_run_success(store):
    run_id = store.start_run("backup")
    assert run_id is not None and run_id > 0
    store.finish_run(run_id, exit_code=0)
    row = store.get_last_run("backup")
    assert row["status"] == "success"
    assert row["exit_code"] == 0
    assert row["duration_s"] is not None


def test_start_and_finish_run_failure(store):
    run_id = store.start_run("report")
    store.finish_run(run_id, exit_code=1)
    row = store.get_last_run("report")
    assert row["status"] == "failure"
    assert row["exit_code"] == 1


def test_running_status_before_finish(store):
    store.start_run("cleanup")
    row = store.get_last_run("cleanup")
    assert row["status"] == "running"
    assert row["finished_at"] is None


def test_duration_is_positive(store):
    started = datetime.utcnow() - timedelta(seconds=5)
    run_id = store.start_run("sync", started_at=started)
    store.finish_run(run_id, exit_code=0)
    row = store.get_last_run("sync")
    assert row["duration_s"] >= 5.0


def test_get_runs_returns_multiple(store):
    for _ in range(3):
        rid = store.start_run("nightly")
        store.finish_run(rid, exit_code=0)
    rows = store.get_runs("nightly")
    assert len(rows) == 3


def test_get_last_run_returns_none_for_unknown(store):
    assert store.get_last_run("nonexistent") is None
