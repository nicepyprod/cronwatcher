"""Utilities for filtering job names by label criteria.

Provides a small query DSL so callers can express things like
``team=platform AND env=prod`` without writing raw SQL.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronwatcher.job_labels import JobLabels


@dataclass
class LabelSelector:
    """A set of required key/value label pairs (AND semantics)."""

    required: Dict[str, str] = field(default_factory=dict)
    present: List[str] = field(default_factory=list)  # key must exist, any value

    def matches(self, labels: Dict[str, str]) -> bool:
        """Return True when *labels* satisfies every constraint."""
        for key, value in self.required.items():
            if labels.get(key) != value:
                return False
        for key in self.present:
            if key not in labels:
                return False
        return True


class LabelFilter:
    """Filters a list of job names using a :class:`LabelSelector`."""

    def __init__(self, store: JobLabels) -> None:
        self._store = store

    def filter(
        self,
        job_names: List[str],
        selector: LabelSelector,
    ) -> List[str]:
        """Return the subset of *job_names* whose labels match *selector*."""
        result: List[str] = []
        for name in job_names:
            labels = self._store.get_labels(name)
            if selector.matches(labels):
                result.append(name)
        return result

    def all_matching(
        self,
        selector: LabelSelector,
        candidate_jobs: Optional[List[str]] = None,
    ) -> List[str]:
        """Return all jobs matching *selector*.

        If *candidate_jobs* is given only those names are considered;
        otherwise every job that has at least one label is searched.
        """
        if candidate_jobs is not None:
            return self.filter(candidate_jobs, selector)

        # Derive candidates from the first required key or first present key.
        if selector.required:
            first_key, first_val = next(iter(selector.required.items()))
            candidates = self._store.jobs_with_label(first_key, first_val)
        elif selector.present:
            candidates = self._store.jobs_with_label(selector.present[0])
        else:
            return []  # empty selector — nothing to do

        return self.filter(candidates, selector)
