"""Tests for QuotaChecker."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cronwatcher.job_quota import JobQuotaStore
from cronwatcher.quota_checker import QuotaChecker


@pytest.fixture()
def quota_store() -> JobQuotaStore:
    return JobQuotaStore(db_path=":memory:")


def _make_run_store(count: int) -> MagicMock:
    rs = MagicMock()
    rs.count_runs_since.return_value = count
    return rs


def test_no_violation_when_no_quota(quota_store: JobQuotaStore) -> None:
    checker = QuotaChecker(quota_store, _make_run_store(99))
    assert checker.check("unknown_job") is None


def test_no_violation_when_within_quota(quota_store: JobQuotaStore) -> None:
    quota_store.set_quota("sync", max_runs=5, window_seconds=3600)
    checker = QuotaChecker(quota_store, _make_run_store(5))
    assert checker.check("sync") is None


def test_violation_when_over_quota(quota_store: JobQuotaStore) -> None:
    quota_store.set_quota("sync", max_runs=5, window_seconds=3600)
    checker = QuotaChecker(quota_store, _make_run_store(6))
    violation = checker.check("sync")
    assert violation is not None
    assert violation.job_name == "sync"
    assert violation.actual_runs == 6
    assert violation.max_runs == 5


def test_is_allowed_returns_true_within_quota(quota_store: JobQuotaStore) -> None:
    quota_store.set_quota("backup", max_runs=3, window_seconds=600)
    checker = QuotaChecker(quota_store, _make_run_store(2))
    assert checker.is_allowed("backup") is True


def test_is_allowed_returns_false_over_quota(quota_store: JobQuotaStore) -> None:
    quota_store.set_quota("backup", max_runs=3, window_seconds=600)
    checker = QuotaChecker(quota_store, _make_run_store(4))
    assert checker.is_allowed("backup") is False


def test_is_allowed_returns_true_when_no_quota(quota_store: JobQuotaStore) -> None:
    checker = QuotaChecker(quota_store, _make_run_store(999))
    assert checker.is_allowed("no_quota_job") is True


def test_check_all_returns_only_violations(quota_store: JobQuotaStore) -> None:
    quota_store.set_quota("job_ok", max_runs=10, window_seconds=3600)
    quota_store.set_quota("job_bad", max_runs=2, window_seconds=3600)

    run_store = MagicMock()
    run_store.count_runs_since.side_effect = lambda name, since: 3 if name == "job_bad" else 1

    checker = QuotaChecker(quota_store, run_store)
    violations = checker.check_all()
    assert len(violations) == 1
    assert violations[0].job_name == "job_bad"


def test_check_all_empty_when_no_quotas(quota_store: JobQuotaStore) -> None:
    checker = QuotaChecker(quota_store, _make_run_store(0))
    assert checker.check_all() == []
