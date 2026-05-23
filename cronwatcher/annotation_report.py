"""Build a human-readable annotation summary for a set of jobs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from cronwatcher.job_annotations import JobAnnotations


@dataclass
class JobAnnotationSummary:
    job_name: str
    annotations: Dict[str, str] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return len(self.annotations) == 0


@dataclass
class AnnotationReport:
    summaries: List[JobAnnotationSummary] = field(default_factory=list)

    @property
    def total_jobs(self) -> int:
        return len(self.summaries)

    @property
    def jobs_with_annotations(self) -> int:
        return sum(1 for s in self.summaries if not s.is_empty)

    def for_job(self, job_name: str) -> JobAnnotationSummary | None:
        return next((s for s in self.summaries if s.job_name == job_name), None)


class AnnotationReporter:
    """Collect annotation data from *JobAnnotations* for a list of job names."""

    def __init__(self, store: JobAnnotations) -> None:
        self._store = store

    def build_report(self, job_names: List[str]) -> AnnotationReport:
        summaries = [
            JobAnnotationSummary(
                job_name=name,
                annotations=self._store.get_all(name),
            )
            for name in sorted(job_names)
        ]
        return AnnotationReport(summaries=summaries)

    def format_text(self, report: AnnotationReport) -> str:
        """Return a plain-text representation of *report*."""
        if not report.summaries:
            return "No jobs found."

        lines: list[str] = [
            f"Annotation Report  ({report.jobs_with_annotations}/{report.total_jobs} jobs annotated)",
            "=" * 60,
        ]
        for summary in report.summaries:
            lines.append(f"  {summary.job_name}")
            if summary.is_empty:
                lines.append("    (no annotations)")
            else:
                for k, v in sorted(summary.annotations.items()):
                    lines.append(f"    {k}: {v}")
        return "\n".join(lines)
