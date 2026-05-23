"""Tests for cronwatcher.job_labels and cronwatcher.label_filter."""

import pytest

from cronwatcher.job_labels import JobLabels
from cronwatcher.label_filter import LabelFilter, LabelSelector


@pytest.fixture()
def store() -> JobLabels:
    return JobLabels()  # in-memory SQLite


@pytest.fixture()
def label_filter(store: JobLabels) -> LabelFilter:
    return LabelFilter(store)


# ---------------------------------------------------------------------------
# JobLabels unit tests
# ---------------------------------------------------------------------------

def test_set_and_get_label(store: JobLabels) -> None:
    store.set_label("backup", "team", "ops")
    assert store.get_labels("backup") == {"team": "ops"}


def test_multiple_labels_for_same_job(store: JobLabels) -> None:
    store.set_label("backup", "team", "ops")
    store.set_label("backup", "env", "prod")
    labels = store.get_labels("backup")
    assert labels == {"team": "ops", "env": "prod"}


def test_overwrite_existing_label(store: JobLabels) -> None:
    store.set_label("backup", "env", "staging")
    store.set_label("backup", "env", "prod")
    assert store.get_labels("backup")["env"] == "prod"


def test_remove_label(store: JobLabels) -> None:
    store.set_label("backup", "team", "ops")
    store.remove_label("backup", "team")
    assert store.get_labels("backup") == {}


def test_get_labels_unknown_job_returns_empty(store: JobLabels) -> None:
    assert store.get_labels("nonexistent") == {}


def test_jobs_with_label_key_only(store: JobLabels) -> None:
    store.set_label("job_a", "env", "prod")
    store.set_label("job_b", "env", "staging")
    store.set_label("job_c", "team", "ops")
    result = store.jobs_with_label("env")
    assert set(result) == {"job_a", "job_b"}


def test_jobs_with_label_key_and_value(store: JobLabels) -> None:
    store.set_label("job_a", "env", "prod")
    store.set_label("job_b", "env", "staging")
    result = store.jobs_with_label("env", "prod")
    assert result == ["job_a"]


def test_clear_job_removes_all_labels(store: JobLabels) -> None:
    store.set_label("cleanup", "team", "ops")
    store.set_label("cleanup", "env", "prod")
    store.clear_job("cleanup")
    assert store.get_labels("cleanup") == {}


# ---------------------------------------------------------------------------
# LabelSelector unit tests
# ---------------------------------------------------------------------------

def test_selector_matches_required() -> None:
    sel = LabelSelector(required={"env": "prod"})
    assert sel.matches({"env": "prod", "team": "ops"})
    assert not sel.matches({"env": "staging"})


def test_selector_matches_present() -> None:
    sel = LabelSelector(present=["critical"])
    assert sel.matches({"critical": "true"})
    assert not sel.matches({"env": "prod"})


# ---------------------------------------------------------------------------
# LabelFilter unit tests
# ---------------------------------------------------------------------------

def test_filter_returns_matching_jobs(store: JobLabels, label_filter: LabelFilter) -> None:
    store.set_label("job_a", "env", "prod")
    store.set_label("job_b", "env", "staging")
    store.set_label("job_c", "env", "prod")
    sel = LabelSelector(required={"env": "prod"})
    result = label_filter.filter(["job_a", "job_b", "job_c"], sel)
    assert set(result) == {"job_a", "job_c"}


def test_all_matching_uses_store_index(store: JobLabels, label_filter: LabelFilter) -> None:
    store.set_label("job_x", "team", "platform")
    store.set_label("job_y", "team", "platform")
    store.set_label("job_z", "team", "data")
    sel = LabelSelector(required={"team": "platform"})
    result = label_filter.all_matching(sel)
    assert set(result) == {"job_x", "job_y"}


def test_all_matching_empty_selector_returns_empty(label_filter: LabelFilter) -> None:
    assert label_filter.all_matching(LabelSelector()) == []
