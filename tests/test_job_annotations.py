"""Tests for JobAnnotations and AnnotationReporter."""

from __future__ import annotations

import pytest

from cronwatcher.job_annotations import JobAnnotations
from cronwatcher.annotation_report import AnnotationReport, AnnotationReporter


@pytest.fixture()
def store() -> JobAnnotations:
    return JobAnnotations(db_path=":memory:")


@pytest.fixture()
def reporter(store: JobAnnotations) -> AnnotationReporter:
    return AnnotationReporter(store)


# ---------------------------------------------------------------------------
# JobAnnotations – basic CRUD
# ---------------------------------------------------------------------------

def test_set_and_get_annotation(store: JobAnnotations) -> None:
    store.set_annotation("backup", "owner", "alice")
    assert store.get_annotation("backup", "owner") == "alice"


def test_get_annotation_returns_none_when_absent(store: JobAnnotations) -> None:
    assert store.get_annotation("backup", "missing_key") is None


def test_overwrite_existing_annotation(store: JobAnnotations) -> None:
    store.set_annotation("backup", "owner", "alice")
    store.set_annotation("backup", "owner", "bob")
    assert store.get_annotation("backup", "owner") == "bob"


def test_get_all_returns_dict(store: JobAnnotations) -> None:
    store.set_annotation("cleanup", "team", "ops")
    store.set_annotation("cleanup", "env", "prod")
    result = store.get_all("cleanup")
    assert result == {"team": "ops", "env": "prod"}


def test_get_all_empty_for_unknown_job(store: JobAnnotations) -> None:
    assert store.get_all("unknown_job") == {}


def test_delete_annotation_returns_true(store: JobAnnotations) -> None:
    store.set_annotation("sync", "note", "important")
    assert store.delete_annotation("sync", "note") is True
    assert store.get_annotation("sync", "note") is None


def test_delete_annotation_returns_false_when_absent(store: JobAnnotations) -> None:
    assert store.delete_annotation("sync", "ghost") is False


def test_delete_all_removes_all_entries(store: JobAnnotations) -> None:
    store.set_annotation("job", "a", "1")
    store.set_annotation("job", "b", "2")
    count = store.delete_all("job")
    assert count == 2
    assert store.get_all("job") == {}


# ---------------------------------------------------------------------------
# AnnotationReporter
# ---------------------------------------------------------------------------

def test_build_report_includes_all_jobs(store: JobAnnotations, reporter: AnnotationReporter) -> None:
    store.set_annotation("job_a", "owner", "alice")
    report = reporter.build_report(["job_a", "job_b"])
    assert report.total_jobs == 2


def test_jobs_with_annotations_count(store: JobAnnotations, reporter: AnnotationReporter) -> None:
    store.set_annotation("job_a", "owner", "alice")
    report = reporter.build_report(["job_a", "job_b"])
    assert report.jobs_with_annotations == 1


def test_for_job_returns_correct_summary(store: JobAnnotations, reporter: AnnotationReporter) -> None:
    store.set_annotation("job_a", "env", "staging")
    report = reporter.build_report(["job_a"])
    summary = report.for_job("job_a")
    assert summary is not None
    assert summary.annotations["env"] == "staging"


def test_format_text_no_jobs(reporter: AnnotationReporter) -> None:
    report = AnnotationReport(summaries=[])
    assert reporter.format_text(report) == "No jobs found."


def test_format_text_contains_job_name(store: JobAnnotations, reporter: AnnotationReporter) -> None:
    store.set_annotation("nightly", "owner", "ops")
    report = reporter.build_report(["nightly"])
    text = reporter.format_text(report)
    assert "nightly" in text
    assert "owner: ops" in text
