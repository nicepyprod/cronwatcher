"""Filter alert events by minimum job priority before forwarding."""
from __future__ import annotations

from typing import Iterable, List

from cronwatcher.job_priority import JobPriorityStore, Priority
from cronwatcher.notifier import AlertEvent


class PriorityAlertFilter:
    """Drops alert events whose job priority is below *min_priority*."""

    def __init__(
        self,
        priority_store: JobPriorityStore,
        min_priority: Priority = Priority.NORMAL,
    ) -> None:
        self._store = priority_store
        self._min_priority = min_priority

    def is_allowed(self, event: AlertEvent) -> bool:
        """Return True if the event's job meets the minimum priority."""
        job_priority = self._store.get_priority(event.job_name)
        return job_priority >= self._min_priority

    def filter(self, events: Iterable[AlertEvent]) -> List[AlertEvent]:
        """Return only events whose job priority meets the threshold."""
        return [e for e in events if self.is_allowed(e)]

    @property
    def min_priority(self) -> Priority:
        return self._min_priority

    @min_priority.setter
    def min_priority(self, value: Priority) -> None:
        self._min_priority = value
