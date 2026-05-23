"""Tests for JobQuotaStore."""

import pytest

from cronwatcher.job_quota import JobQuotaStore, QuotaEntry


@pytest.fixture()
def store() -> JobQuotaStore:
    return JobQuotaStore(db_path=":memory:")


def test_get_returns_none_when_not_set(store: JobQuotaStore) -> None:
    assert store.get_quota("backup") is None


def test_set_and_get_quota(store: JobQuotaStore) -> None:
    store.set_quota("backup", max_runs=3, window_seconds=3600)
    entry = store.get_quota("backup")
    assert entry is not None
    assert entry.job_name == "backup"
    assert entry.max_runs == 3
    assert entry.window_seconds == 3600


def test_overwrite_existing_quota(store: JobQuotaStore) -> None:
    store.set_quota("backup", max_runs=3, window_seconds=3600)
    store.set_quota("backup", max_runs=10, window_seconds=7200)
    entry = store.get_quota("backup")
    assert entry is not None
    assert entry.max_runs == 10
    assert entry.window_seconds == 7200


def test_remove_quota(store: JobQuotaStore) -> None:
    store.set_quota("cleanup", max_runs=1, window_seconds=86400)
    store.remove_quota("cleanup")
    assert store.get_quota("cleanup") is None


def test_remove_nonexistent_quota_is_safe(store: JobQuotaStore) -> None:
    store.remove_quota("ghost")  # should not raise


def test_all_quotas_empty(store: JobQuotaStore) -> None:
    assert store.all_quotas() == []


def test_all_quotas_returns_all(store: JobQuotaStore) -> None:
    store.set_quota("job_a", max_runs=5, window_seconds=600)
    store.set_quota("job_b", max_runs=2, window_seconds=1800)
    names = {e.job_name for e in store.all_quotas()}
    assert names == {"job_a", "job_b"}


def test_quota_violation_str() -> None:
    from cronwatcher.job_quota import QuotaViolation

    v = QuotaViolation(job_name="sync", window_seconds=3600, max_runs=5, actual_runs=7)
    text = str(v)
    assert "sync" in text
    assert "7/5" in text
    assert "3600" in text
