"""Tests for cronwatcher.job_pause."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from cronwatcher.job_pause import JobPauseStore


@pytest.fixture()
def store() -> JobPauseStore:
    return JobPauseStore(db_path=":memory:")


def _utc(**kwargs) -> datetime:
    return datetime.now(timezone.utc) + timedelta(**kwargs)


class TestPause:
    def test_pause_makes_job_paused(self, store: JobPauseStore) -> None:
        store.pause("backup")
        assert store.is_paused("backup")

    def test_unparsed_job_is_not_paused(self, store: JobPauseStore) -> None:
        assert not store.is_paused("backup")

    def test_pause_stores_reason(self, store: JobPauseStore) -> None:
        store.pause("backup", reason="maintenance window")
        entry = store.get("backup")
        assert entry is not None
        assert entry.reason == "maintenance window"

    def test_pause_with_future_until_is_active(self, store: JobPauseStore) -> None:
        until = _utc(hours=2)
        store.pause("backup", paused_until=until)
        assert store.is_paused("backup")

    def test_pause_with_past_until_is_not_active(self, store: JobPauseStore) -> None:
        until = _utc(hours=-1)
        store.pause("backup", paused_until=until)
        assert not store.is_paused("backup")

    def test_pause_overwrites_previous_pause(self, store: JobPauseStore) -> None:
        store.pause("backup", reason="first")
        store.pause("backup", reason="second")
        entry = store.get("backup")
        assert entry is not None
        assert entry.reason == "second"


class TestResume:
    def test_resume_removes_pause(self, store: JobPauseStore) -> None:
        store.pause("backup")
        result = store.resume("backup")
        assert result is True
        assert not store.is_paused("backup")

    def test_resume_returns_false_when_not_paused(self, store: JobPauseStore) -> None:
        result = store.resume("nonexistent")
        assert result is False

    def test_get_returns_none_after_resume(self, store: JobPauseStore) -> None:
        store.pause("backup")
        store.resume("backup")
        assert store.get("backup") is None


class TestAllPaused:
    def test_all_paused_empty_when_none(self, store: JobPauseStore) -> None:
        assert store.all_paused() == []

    def test_all_paused_returns_multiple_entries(self, store: JobPauseStore) -> None:
        store.pause("job_a")
        store.pause("job_b", reason="deploy")
        entries = store.all_paused()
        names = {e.job_name for e in entries}
        assert names == {"job_a", "job_b"}

    def test_all_paused_excludes_resumed_jobs(self, store: JobPauseStore) -> None:
        store.pause("job_a")
        store.pause("job_b")
        store.resume("job_a")
        entries = store.all_paused()
        assert len(entries) == 1
        assert entries[0].job_name == "job_b"
