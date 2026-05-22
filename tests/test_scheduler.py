"""Tests for MissedRunDetector."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cronwatcher.config import JobConfig
from cronwatcher.scheduler import MissedRunDetector


@pytest.fixture()
def job() -> JobConfig:
    return JobConfig(name="backup", schedule="* * * * *")  # every minute


@pytest.fixture()
def store() -> MagicMock:
    return MagicMock()


def _ts(dt: datetime) -> float:
    return dt.timestamp()


class TestLastExpectedRun:
    def test_returns_datetime(self, job: JobConfig, store: MagicMock) -> None:
        detector = MissedRunDetector(store)
        now = datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        result = detector.last_expected_run(job, now)
        assert isinstance(result, datetime)
        assert result < now

    def test_expected_is_before_now(self, job: JobConfig, store: MagicMock) -> None:
        detector = MissedRunDetector(store)
        now = datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        expected = detector.last_expected_run(job, now)
        assert expected <= now


class TestIsMissed:
    def test_not_missed_when_run_after_expected(self, job: JobConfig, store: MagicMock) -> None:
        detector = MissedRunDetector(store, grace_seconds=60)
        now = datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        expected = detector.last_expected_run(job, now)
        store.last_run.return_value = {"started_at": _ts(expected) + 1}
        assert detector.is_missed(job, now) is False

    def test_missed_when_no_run_recorded_and_past_grace(self, job: JobConfig, store: MagicMock) -> None:
        detector = MissedRunDetector(store, grace_seconds=0)
        now = datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        store.last_run.return_value = None
        assert detector.is_missed(job, now) is True

    def test_missed_when_last_run_before_expected(self, job: JobConfig, store: MagicMock) -> None:
        detector = MissedRunDetector(store, grace_seconds=0)
        now = datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        expected = detector.last_expected_run(job, now)
        store.last_run.return_value = {"started_at": _ts(expected) - 120}
        assert detector.is_missed(job, now) is True

    def test_not_missed_within_grace_period(self, job: JobConfig, store: MagicMock) -> None:
        detector = MissedRunDetector(store, grace_seconds=300)
        now = datetime(2024, 1, 15, 12, 30, 10, tzinfo=timezone.utc)
        expected = detector.last_expected_run(job, now)
        store.last_run.return_value = {"started_at": _ts(expected) - 30}
        # still within grace — deadline not yet passed
        assert detector.is_missed(job, now) is False


class TestCheckAll:
    def test_returns_empty_when_no_jobs(self, store: MagicMock) -> None:
        detector = MissedRunDetector(store)
        assert detector.check_all([], datetime.now(tz=timezone.utc)) == []

    def test_returns_missed_job_names(self, store: MagicMock) -> None:
        detector = MissedRunDetector(store, grace_seconds=0)
        jobs = [JobConfig(name="job1", schedule="* * * * *")]
        now = datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        store.last_run.return_value = None
        result = detector.check_all(jobs, now)
        assert "job1" in result
