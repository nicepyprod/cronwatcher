"""Tests for JobRegistry and RegistryDiff."""

import pytest

from cronwatcher.config import JobConfig
from cronwatcher.job_registry import JobRegistry, RegistryDiff


def _job(name: str) -> JobConfig:
    return JobConfig(name=name, schedule="* * * * *", command=f"echo {name}")


@pytest.fixture
def registry() -> JobRegistry:
    return JobRegistry()


def test_load_populates_registry(registry: JobRegistry) -> None:
    registry.load([_job("a"), _job("b")])
    assert set(registry.names()) == {"a", "b"}
    assert len(registry) == 2


def test_get_returns_job(registry: JobRegistry) -> None:
    registry.load([_job("alpha")])
    job = registry.get("alpha")
    assert job is not None
    assert job.name == "alpha"


def test_get_returns_none_for_unknown(registry: JobRegistry) -> None:
    registry.load([_job("alpha")])
    assert registry.get("missing") is None


def test_sync_detects_added_jobs(registry: JobRegistry) -> None:
    registry.load([_job("a")])
    diff = registry.sync([_job("a"), _job("b")])
    assert len(diff.added) == 1
    assert diff.added[0].name == "b"
    assert diff.removed == []
    assert diff.has_changes


def test_sync_detects_removed_jobs(registry: JobRegistry) -> None:
    registry.load([_job("a"), _job("b")])
    diff = registry.sync([_job("a")])
    assert diff.removed == ["b"]
    assert diff.added == []
    assert diff.has_changes


def test_sync_no_changes(registry: JobRegistry) -> None:
    registry.load([_job("a"), _job("b")])
    diff = registry.sync([_job("a"), _job("b")])
    assert not diff.has_changes


def test_sync_updates_registry(registry: JobRegistry) -> None:
    registry.load([_job("a")])
    registry.sync([_job("b"), _job("c")])
    assert set(registry.names()) == {"b", "c"}


def test_all_returns_list(registry: JobRegistry) -> None:
    jobs = [_job("x"), _job("y")]
    registry.load(jobs)
    assert len(registry.all()) == 2
