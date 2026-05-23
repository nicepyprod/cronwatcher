"""Tests for cronwatcher.rate_limiter."""

from __future__ import annotations

import time

import pytest

from cronwatcher.rate_limiter import AlertRateLimiter


@pytest.fixture
def limiter() -> AlertRateLimiter:
    return AlertRateLimiter(db_path=":memory:", cooldown_seconds=60)


class TestIsAllowed:
    def test_allowed_when_no_prior_record(self, limiter: AlertRateLimiter) -> None:
        assert limiter.is_allowed("backup", "failure") is True

    def test_not_allowed_immediately_after_record(self, limiter: AlertRateLimiter) -> None:
        limiter.record_sent("backup", "failure")
        assert limiter.is_allowed("backup", "failure") is False

    def test_allowed_after_cooldown_expires(self, limiter: AlertRateLimiter) -> None:
        # Use a very short cooldown for the test
        fast_limiter = AlertRateLimiter(db_path=":memory:", cooldown_seconds=0)
        fast_limiter.record_sent("backup", "failure")
        time.sleep(0.01)
        assert fast_limiter.is_allowed("backup", "failure") is True

    def test_different_alert_types_are_independent(self, limiter: AlertRateLimiter) -> None:
        limiter.record_sent("backup", "failure")
        assert limiter.is_allowed("backup", "missed") is True

    def test_different_jobs_are_independent(self, limiter: AlertRateLimiter) -> None:
        limiter.record_sent("backup", "failure")
        assert limiter.is_allowed("sync", "failure") is True


class TestRecordSent:
    def test_record_updates_existing_entry(self, limiter: AlertRateLimiter) -> None:
        limiter.record_sent("backup", "failure")
        first_entry = limiter._get_entry("backup", "failure")
        time.sleep(0.05)
        limiter.record_sent("backup", "failure")
        second_entry = limiter._get_entry("backup", "failure")
        assert second_entry is not None
        assert first_entry is not None
        assert second_entry.last_sent_at > first_entry.last_sent_at


class TestClear:
    def test_clear_removes_entry(self, limiter: AlertRateLimiter) -> None:
        limiter.record_sent("backup", "failure")
        limiter.clear("backup", "failure")
        assert limiter.is_allowed("backup", "failure") is True

    def test_clear_nonexistent_entry_is_safe(self, limiter: AlertRateLimiter) -> None:
        limiter.clear("nonexistent", "failure")  # should not raise

    def test_clear_only_removes_specified_entry(self, limiter: AlertRateLimiter) -> None:
        limiter.record_sent("backup", "failure")
        limiter.record_sent("backup", "missed")
        limiter.clear("backup", "failure")
        assert limiter.is_allowed("backup", "failure") is True
        assert limiter.is_allowed("backup", "missed") is False
