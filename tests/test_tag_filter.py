"""Tests for cronwatcher.tag_filter."""

import pytest

from cronwatcher.job_tags import JobTags
from cronwatcher.tag_filter import TagFilter


@pytest.fixture()
def tags() -> JobTags:
    store = JobTags(db_path=":memory:")
    store.add_tag("backup", "critical")
    store.add_tag("backup", "nightly")
    store.add_tag("cleanup", "nightly")
    store.add_tag("report", "weekly")
    return store


@pytest.fixture()
def tag_filter(tags: JobTags) -> TagFilter:
    return TagFilter(tags)


ALL_JOBS = ["backup", "cleanup", "report"]


def test_filter_no_required_tags_returns_all(tag_filter: TagFilter) -> None:
    assert tag_filter.filter(ALL_JOBS, []) == ALL_JOBS


def test_filter_single_tag(tag_filter: TagFilter) -> None:
    result = tag_filter.filter(ALL_JOBS, ["nightly"])
    assert result == ["backup", "cleanup"]


def test_filter_multiple_tags_and_semantics(tag_filter: TagFilter) -> None:
    result = tag_filter.filter(ALL_JOBS, ["critical", "nightly"])
    assert result == ["backup"]


def test_filter_no_match_returns_empty(tag_filter: TagFilter) -> None:
    result = tag_filter.filter(ALL_JOBS, ["critical", "weekly"])
    assert result == []


def test_filter_unknown_tag_returns_empty(tag_filter: TagFilter) -> None:
    result = tag_filter.filter(ALL_JOBS, ["ghost"])
    assert result == []


def test_jobs_matching_any_empty_tags_returns_all(tag_filter: TagFilter) -> None:
    assert tag_filter.jobs_matching_any(ALL_JOBS, []) == ALL_JOBS


def test_jobs_matching_any_single_tag(tag_filter: TagFilter) -> None:
    result = tag_filter.jobs_matching_any(ALL_JOBS, ["critical"])
    assert result == ["backup"]


def test_jobs_matching_any_multiple_tags(tag_filter: TagFilter) -> None:
    result = tag_filter.jobs_matching_any(ALL_JOBS, ["critical", "weekly"])
    assert sorted(result) == ["backup", "report"]


def test_filter_ignores_whitespace_in_tag(tag_filter: TagFilter) -> None:
    result = tag_filter.filter(ALL_JOBS, ["  nightly  "])
    assert result == ["backup", "cleanup"]
