"""Produce a priority-aware summary of job health."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from cronwatcher.job_priority import JobPriorityStore, Priority
from cronwatcher.reporter import Report, JobSummary


@dataclass
class PriorityGroup:
    priority: Priority
    summaries: List[JobSummary] = field(default_factory=list)

    @property
    def total_failures(self) -> int:
        return sum(s.failure_count for s in self.summaries)

    @property
    def has_failures(self) -> bool:
        return self.total_failures > 0


class PriorityReport:
    """Groups a Report's summaries by their assigned job priority."""

    def __init__(self, report: Report, priority_store: JobPriorityStore) -> None:
        self._report = report
        self._store = priority_store
        self._groups: Dict[Priority, PriorityGroup] = {
            p: PriorityGroup(priority=p) for p in Priority
        }
        self._build()

    def _build(self) -> None:
        for summary in self._report.summaries:
            p = self._store.get_priority(summary.job_name)
            self._groups[p].summaries.append(summary)

    def group(self, priority: Priority) -> PriorityGroup:
        return self._groups[priority]

    def groups_with_failures(self) -> List[PriorityGroup]:
        return [
            g for g in sorted(self._groups.values(), key=lambda g: -g.priority.value)
            if g.has_failures
        ]

    def critical_failures(self) -> List[JobSummary]:
        return [
            s for s in self._groups[Priority.CRITICAL].summaries
            if s.failure_count > 0
        ]
