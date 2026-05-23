"""Tests for cronwatcher.metrics."""

import pytest
from cronwatcher.metrics import JobMetrics, MetricsCollector


@pytest.fixture
def collector() -> MetricsCollector:
    return MetricsCollector()


class TestJobMetrics:
    def test_avg_duration_zero_when_no_runs(self):
        m = JobMetrics(job_name="backup")
        assert m.avg_duration_seconds == 0.0

    def test_success_rate_one_when_no_runs(self):
        m = JobMetrics(job_name="backup")
        assert m.success_rate == 1.0

    def test_as_dict_contains_expected_keys(self):
        m = JobMetrics(job_name="backup", run_count=2, failure_count=1, total_duration_seconds=10.0)
        d = m.as_dict()
        assert d["job_name"] == "backup"
        assert d["run_count"] == 2
        assert d["failure_count"] == 1
        assert d["avg_duration_seconds"] == 5.0
        assert d["success_rate"] == 0.5


class TestMetricsCollector:
    def test_record_creates_entry(self, collector):
        collector.record("sync", 3.5, success=True)
        m = collector.get("sync")
        assert m is not None
        assert m.run_count == 1
        assert m.failure_count == 0

    def test_record_failure_increments_failure_count(self, collector):
        collector.record("sync", 1.0, success=False)
        m = collector.get("sync")
        assert m.failure_count == 1

    def test_multiple_records_accumulate(self, collector):
        collector.record("sync", 2.0, success=True)
        collector.record("sync", 4.0, success=True)
        m = collector.get("sync")
        assert m.run_count == 2
        assert m.total_duration_seconds == 6.0
        assert m.avg_duration_seconds == 3.0

    def test_get_returns_none_for_unknown_job(self, collector):
        assert collector.get("nonexistent") is None

    def test_all_returns_all_jobs(self, collector):
        collector.record("jobA", 1.0, success=True)
        collector.record("jobB", 2.0, success=False)
        names = {m.job_name for m in collector.all()}
        assert names == {"jobA", "jobB"}

    def test_reset_clears_metrics(self, collector):
        collector.record("jobA", 1.0, success=True)
        collector.reset()
        assert collector.all() == []

    def test_success_rate_mixed(self, collector):
        collector.record("job", 1.0, success=True)
        collector.record("job", 1.0, success=True)
        collector.record("job", 1.0, success=False)
        m = collector.get("job")
        assert abs(m.success_rate - (2 / 3)) < 1e-9
