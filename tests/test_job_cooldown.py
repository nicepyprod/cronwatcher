"""Tests for job cooldown enforcement."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from cronwatcher.job_cooldown import (
    CooldownChecker,
    CooldownViolation,
    JobCooldownStore,
)


@pytest.fixture()
def store() -> JobCooldownStore:
    return JobCooldownStore(db_path=":memory:")


@pytest.fixture()
def checker(store: JobCooldownStore) -> CooldownChecker:
    return CooldownChecker(cooldown_store=store)


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


# --- JobCooldownStore ---


def test_get_returns_none_when_not_set(store: JobCooldownStore) -> None:
    assert store.get_cooldown("myjob") is None


def test_set_and_get_cooldown(store: JobCooldownStore) -> None:
    store.set_cooldown("myjob", 300)
    assert store.get_cooldown("myjob") == 300


def test_overwrite_existing_cooldown(store: JobCooldownStore) -> None:
    store.set_cooldown("myjob", 300)
    store.set_cooldown("myjob", 600)
    assert store.get_cooldown("myjob") == 600


def test_remove_cooldown(store: JobCooldownStore) -> None:
    store.set_cooldown("myjob", 300)
    store.remove_cooldown("myjob")
    assert store.get_cooldown("myjob") is None


def test_remove_nonexistent_is_noop(store: JobCooldownStore) -> None:
    store.remove_cooldown("ghost")  # should not raise


# --- CooldownChecker ---


def test_no_violation_when_no_cooldown_set(
    checker: CooldownChecker, store: JobCooldownStore
) -> None:
    last_run = _now() - timedelta(seconds=5)
    assert checker.check("myjob", last_run) is None


def test_no_violation_when_last_run_is_none(
    checker: CooldownChecker, store: JobCooldownStore
) -> None:
    store.set_cooldown("myjob", 300)
    assert checker.check("myjob", None) is None


def test_violation_when_within_cooldown(
    checker: CooldownChecker, store: JobCooldownStore
) -> None:
    store.set_cooldown("myjob", 300)
    last_run = _now() - timedelta(seconds=60)
    violation = checker.check("myjob", last_run)
    assert isinstance(violation, CooldownViolation)
    assert violation.job_name == "myjob"
    assert violation.cooldown_seconds == 300


def test_no_violation_after_cooldown_expires(
    checker: CooldownChecker, store: JobCooldownStore
) -> None:
    store.set_cooldown("myjob", 300)
    last_run = _now() - timedelta(seconds=400)
    assert checker.check("myjob", last_run) is None


def test_earliest_next_run_is_correct(
    checker: CooldownChecker, store: JobCooldownStore
) -> None:
    store.set_cooldown("myjob", 300)
    last_run = _now() - timedelta(seconds=60)
    violation = checker.check("myjob", last_run)
    assert violation is not None
    expected = last_run + timedelta(seconds=300)
    assert abs((violation.earliest_next_run - expected).total_seconds()) < 1


def test_is_in_cooldown_returns_bool(
    checker: CooldownChecker, store: JobCooldownStore
) -> None:
    store.set_cooldown("myjob", 300)
    last_run = _now() - timedelta(seconds=60)
    assert checker.is_in_cooldown("myjob", last_run) is True


def test_violation_str_contains_job_name(
    checker: CooldownChecker, store: JobCooldownStore
) -> None:
    store.set_cooldown("myjob", 300)
    last_run = _now() - timedelta(seconds=60)
    violation = checker.check("myjob", last_run)
    assert "myjob" in str(violation)
