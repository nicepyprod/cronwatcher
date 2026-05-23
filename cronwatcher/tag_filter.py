"""Filter job names by tag expressions."""

from __future__ import annotations

from typing import Iterable, List

from cronwatcher.job_tags import JobTags


class TagFilter:
    """Return job names that match ALL required tags (AND semantics)."""

    def __init__(self, tags: JobTags) -> None:
        self._tags = tags

    def filter(self, job_names: Iterable[str], required_tags: Iterable[str]) -> List[str]:
        """Return jobs from *job_names* that carry every tag in *required_tags*.

        If *required_tags* is empty every job is returned unchanged.
        """
        required = [t.strip().lower() for t in required_tags if t.strip()]
        if not required:
            return list(job_names)

        result: List[str] = []
        for name in job_names:
            job_tag_set = set(self._tags.get_tags(name))
            if all(rt in job_tag_set for rt in required):
                result.append(name)
        return result

    def jobs_matching_any(self, job_names: Iterable[str], any_tags: Iterable[str]) -> List[str]:
        """Return jobs from *job_names* that carry AT LEAST ONE tag in *any_tags*."""
        wanted = {t.strip().lower() for t in any_tags if t.strip()}
        if not wanted:
            return list(job_names)

        result: List[str] = []
        for name in job_names:
            job_tag_set = set(self._tags.get_tags(name))
            if job_tag_set & wanted:
                result.append(name)
        return result
