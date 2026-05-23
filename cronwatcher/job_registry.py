"""Registry for tracking known cron jobs and detecting added/removed jobs."""

from dataclasses import dataclass, field
from typing import Dict, List, Set

from cronwatcher.config import JobConfig


@dataclass
class RegistryDiff:
    added: List[JobConfig] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed)


class JobRegistry:
    """Maintains the current set of known jobs and computes diffs on reload."""

    def __init__(self) -> None:
        self._jobs: Dict[str, JobConfig] = {}

    def load(self, jobs: List[JobConfig]) -> None:
        """Replace the registry with a new list of jobs (initial load)."""
        self._jobs = {job.name: job for job in jobs}

    def sync(self, jobs: List[JobConfig]) -> RegistryDiff:
        """Update the registry and return a diff describing what changed."""
        new_names: Set[str] = {job.name for job in jobs}
        old_names: Set[str] = set(self._jobs.keys())

        added = [job for job in jobs if job.name not in old_names]
        removed = [name for name in old_names if name not in new_names]

        self._jobs = {job.name: job for job in jobs}
        return RegistryDiff(added=added, removed=removed)

    def get(self, name: str) -> JobConfig | None:
        return self._jobs.get(name)

    def all(self) -> List[JobConfig]:
        return list(self._jobs.values())

    def names(self) -> List[str]:
        return list(self._jobs.keys())

    def __len__(self) -> int:
        return len(self._jobs)
