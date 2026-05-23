"""Tests for PriorityAlertFilter."""
import pytest
from unittest.mock import MagicMock

from cronwatcher.job_priority import JobPriorityStore, Priority
from cronwatcher.priority_alert_filter import PriorityAlertFilter
from cronwatcher.notifier import AlertEvent


def _event(job_name: str) -> AlertEvent:
    return AlertEvent(
        job_name=job_name,
        event_type="failure",
        message=f"{job_name} failed",
        timestamp=0.0,
    )


@pytest.fixture
def store() -> JobPriorityStore:
    s = JobPriorityStore(db_path=":memory:")
    s.set_priority("low_job", Priority.LOW)
    s.set_priority("high_job", Priority.HIGH)
    s.set_priority("crit_job", Priority.CRITICAL)
    return s


@pytest.fixture
def alert_filter(store) -> PriorityAlertFilter:
    return PriorityAlertFilter(store, min_priority=Priority.NORMAL)


class TestPriorityAlertFilter:
    def test_allows_event_at_min_priority(self, store):
        f = PriorityAlertFilter(store, min_priority=Priority.NORMAL)
        event = _event("unknown_job")  # defaults to NORMAL
        assert f.is_allowed(event) is True

    def test_blocks_event_below_min_priority(self, alert_filter):
        assert alert_filter.is_allowed(_event("low_job")) is False

    def test_allows_event_above_min_priority(self, alert_filter):
        assert alert_filter.is_allowed(_event("high_job")) is True
        assert alert_filter.is_allowed(_event("crit_job")) is True

    def test_filter_removes_low_priority_events(self, alert_filter):
        events = [_event("low_job"), _event("high_job"), _event("crit_job")]
        result = alert_filter.filter(events)
        names = [e.job_name for e in result]
        assert "low_job" not in names
        assert "high_job" in names
        assert "crit_job" in names

    def test_filter_empty_list_returns_empty(self, alert_filter):
        assert alert_filter.filter([]) == []

    def test_min_priority_can_be_updated(self, alert_filter):
        alert_filter.min_priority = Priority.LOW
        assert alert_filter.is_allowed(_event("low_job")) is True

    def test_critical_only_filter(self, store):
        f = PriorityAlertFilter(store, min_priority=Priority.CRITICAL)
        events = [_event("low_job"), _event("high_job"), _event("crit_job")]
        result = f.filter(events)
        assert len(result) == 1
        assert result[0].job_name == "crit_job"
