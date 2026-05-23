"""Tests for cronwatcher.job_history."""

from __future__ import annotations

import time
import pytest

from cronwatcher.db import JobRunStore
from cronwatcher.job_history import JobHistory, JobHistoryReader, RunRecord


@pytest.fixture
def store(tmp_path):
    return JobRunStore(str(tmp_path / "runs.db"))


@pytest.fixture
def reader(store):
    return JobHistoryReader(store)


def _add_run(store: JobRunStore, job: str, exit_code: int = 0, duration: float = 1.5):
    now = time.time()
    run_id = store.start_run(job, now - duration)
    store.finish_run(run_id, now, exit_code)
    return run_id


class TestJobHistoryReader:
    def test_empty_history_for_unknown_job(self, reader):
        history = reader.get_history("ghost_job")
        assert history.job_name == "ghost_job"
        assert history.total_runs == 0
        assert history.last_run is None

    def test_history_contains_runs(self, store, reader):
        _add_run(store, "backup", exit_code=0)
        _add_run(store, "backup", exit_code=1)
        history = reader.get_history("backup")
        assert history.total_runs == 2

    def test_successful_and_failed_counts(self, store, reader):
        _add_run(store, "sync", exit_code=0)
        _add_run(store, "sync", exit_code=0)
        _add_run(store, "sync", exit_code=2)
        history = reader.get_history("sync")
        assert history.successful_runs == 2
        assert history.failed_runs == 1

    def test_success_rate_all_passing(self, store, reader):
        for _ in range(4):
            _add_run(store, "clean", exit_code=0)
        history = reader.get_history("clean")
        assert history.success_rate == pytest.approx(1.0)

    def test_success_rate_mixed(self, store, reader):
        _add_run(store, "export", exit_code=0)
        _add_run(store, "export", exit_code=1)
        history = reader.get_history("export")
        assert history.success_rate == pytest.approx(0.5)

    def test_avg_duration(self, store, reader):
        _add_run(store, "report", exit_code=0, duration=2.0)
        _add_run(store, "report", exit_code=0, duration=4.0)
        history = reader.get_history("report")
        assert history.avg_duration_seconds == pytest.approx(3.0, abs=0.1)

    def test_avg_duration_none_when_no_runs(self, reader):
        history = reader.get_history("nothing")
        assert history.avg_duration_seconds is None

    def test_limit_is_respected(self, store, reader):
        for _ in range(10):
            _add_run(store, "batch", exit_code=0)
        history = reader.get_history("batch", limit=5)
        assert history.total_runs == 5

    def test_get_histories_returns_one_per_job(self, store, reader):
        _add_run(store, "alpha", exit_code=0)
        _add_run(store, "beta", exit_code=0)
        histories = reader.get_histories(["alpha", "beta", "gamma"])
        assert len(histories) == 3
        names = [h.job_name for h in histories]
        assert "alpha" in names
        assert "gamma" in names
