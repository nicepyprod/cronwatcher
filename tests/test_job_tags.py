"""Tests for cronwatcher.job_tags."""

import pytest

from cronwatcher.job_tags import JobTags


@pytest.fixture()
def store() -> JobTags:
    return JobTags(db_path=":memory:")


def test_add_and_get_tag(store: JobTags) -> None:
    store.add_tag("backup", "critical")
    assert store.get_tags("backup") == ["critical"]


def test_add_multiple_tags_sorted(store: JobTags) -> None:
    store.add_tag("backup", "nightly")
    store.add_tag("backup", "critical")
    assert store.get_tags("backup") == ["critical", "nightly"]


def test_add_tag_is_idempotent(store: JobTags) -> None:
    store.add_tag("backup", "critical")
    store.add_tag("backup", "critical")
    assert store.get_tags("backup") == ["critical"]


def test_tag_normalised_to_lowercase(store: JobTags) -> None:
    store.add_tag("backup", "  CRITICAL  ")
    assert store.get_tags("backup") == ["critical"]


def test_empty_tag_raises(store: JobTags) -> None:
    with pytest.raises(ValueError):
        store.add_tag("backup", "   ")


def test_remove_tag(store: JobTags) -> None:
    store.add_tag("backup", "critical")
    store.add_tag("backup", "nightly")
    store.remove_tag("backup", "critical")
    assert store.get_tags("backup") == ["nightly"]


def test_remove_nonexistent_tag_is_silent(store: JobTags) -> None:
    store.remove_tag("backup", "ghost")  # should not raise


def test_jobs_with_tag(store: JobTags) -> None:
    store.add_tag("backup", "critical")
    store.add_tag("cleanup", "critical")
    store.add_tag("report", "nightly")
    assert store.jobs_with_tag("critical") == ["backup", "cleanup"]


def test_jobs_with_tag_empty_when_none_match(store: JobTags) -> None:
    store.add_tag("backup", "nightly")
    assert store.jobs_with_tag("critical") == []


def test_clear_tags(store: JobTags) -> None:
    store.add_tag("backup", "critical")
    store.add_tag("backup", "nightly")
    store.clear_tags("backup")
    assert store.get_tags("backup") == []


def test_get_tags_unknown_job_returns_empty(store: JobTags) -> None:
    assert store.get_tags("nonexistent") == []
