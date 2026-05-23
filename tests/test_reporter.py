"""Tests for Reporter and JobSummary."""

from datetime import datetime, timedelta

import pytest

from cronwatcher.db import JobRunStore
from cronwatcher.reporter import Reporter, Report


@pytest.fixture
def store():
    return JobRunStore(":memory:")


@pytest.fixture
def reporter(store):
    return Reporter(store)


def _add_run(store, job_name, status, seconds_ago=10):
    run_id = store.start_run(job_name)
    # Patch started_at to be in the past
    started = (datetime.utcnow() - timedelta(seconds=seconds_ago)).isoformat()
    store._conn.execute(
        "UPDATE job_runs SET started_at = ? WHERE id = ?", (started, run_id)
    )
    store._conn.commit()
    store.finish_run(run_id, status)
    return run_id


def test_empty_report(reporter):
    report = reporter.generate([], period_hours=24)
    assert isinstance(report, Report)
    assert report.total_jobs == 0
    assert report.jobs_with_failures == []


def test_summary_counts(store, reporter):
    _add_run(store, "backup", "success")
    _add_run(store, "backup", "success")
    _add_run(store, "backup", "failure")

    report = reporter.generate(["backup"], period_hours=24)
    s = report.summaries[0]
    assert s.job_name == "backup"
    assert s.total_runs == 3
    assert s.successful_runs == 2
    assert s.failed_runs == 1


def test_success_rate(store, reporter):
    _add_run(store, "sync", "success")
    _add_run(store, "sync", "failure")

    report = reporter.generate(["sync"], period_hours=24)
    assert report.summaries[0].success_rate == pytest.approx(50.0)


def test_no_runs_returns_zero_counts(reporter):
    report = reporter.generate(["ghost_job"], period_hours=24)
    s = report.summaries[0]
    assert s.total_runs == 0
    assert s.avg_duration_seconds is None
    assert s.last_run_at is None
    assert s.success_rate == 0.0


def test_jobs_with_failures_filter(store, reporter):
    _add_run(store, "ok_job", "success")
    _add_run(store, "bad_job", "failure")

    report = reporter.generate(["ok_job", "bad_job"], period_hours=24)
    failing = [s.job_name for s in report.jobs_with_failures]
    assert "bad_job" in failing
    assert "ok_job" not in failing


def test_avg_duration_is_positive(store, reporter):
    _add_run(store, "etl", "success", seconds_ago=30)
    report = reporter.generate(["etl"], period_hours=24)
    assert report.summaries[0].avg_duration_seconds > 0
