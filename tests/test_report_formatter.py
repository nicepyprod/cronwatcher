"""Tests for TextFormatter and HtmlFormatter."""

from datetime import datetime

import pytest

from cronwatcher.reporter import Report, JobSummary
from cronwatcher.report_formatter import TextFormatter, HtmlFormatter


@pytest.fixture
def sample_report():
    summaries = [
        JobSummary(
            job_name="backup",
            total_runs=5,
            successful_runs=4,
            failed_runs=1,
            avg_duration_seconds=12.5,
            last_run_at=datetime(2024, 1, 15, 8, 0),
            last_status="success",
        ),
        JobSummary(
            job_name="sync",
            total_runs=3,
            successful_runs=3,
            failed_runs=0,
            avg_duration_seconds=None,
            last_run_at=None,
            last_status=None,
        ),
    ]
    return Report(
        generated_at=datetime(2024, 1, 15, 12, 0),
        period_hours=24,
        summaries=summaries,
    )


class TestTextFormatter:
    def test_contains_job_names(self, sample_report):
        text = TextFormatter().format(sample_report)
        assert "backup" in text
        assert "sync" in text

    def test_contains_failure_warning(self, sample_report):
        text = TextFormatter().format(sample_report)
        assert "backup" in text
        assert "⚠" in text

    def test_na_when_no_duration(self, sample_report):
        text = TextFormatter().format(sample_report)
        assert "N/A" in text

    def test_period_shown(self, sample_report):
        text = TextFormatter().format(sample_report)
        assert "24h" in text


class TestHtmlFormatter:
    def test_is_valid_html_snippet(self, sample_report):
        html = HtmlFormatter().format(sample_report)
        assert "<html>" in html
        assert "</html>" in html

    def test_contains_job_names(self, sample_report):
        html = HtmlFormatter().format(sample_report)
        assert "backup" in html
        assert "sync" in html

    def test_failure_row_highlighted(self, sample_report):
        html = HtmlFormatter().format(sample_report)
        assert "#fdd" in html  # failure colour
        assert "#dfd" in html  # success colour

    def test_na_for_missing_values(self, sample_report):
        html = HtmlFormatter().format(sample_report)
        assert "N/A" in html
