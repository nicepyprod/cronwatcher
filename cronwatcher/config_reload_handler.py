"""Handles config reload: syncs the job registry and emits audit events."""

import logging
from typing import Callable

from cronwatcher.audit_log import AuditLog
from cronwatcher.config import CronWatcherConfig, load_config
from cronwatcher.job_registry import JobRegistry
from cronwatcher import audit_events

logger = logging.getLogger(__name__)


class ConfigReloadHandler:
    """Reloads config from disk, updates the registry, and logs audit events."""

    def __init__(
        self,
        config_path: str,
        registry: JobRegistry,
        audit_log: AuditLog,
        on_config_updated: Callable[[CronWatcherConfig], None] | None = None,
    ) -> None:
        self._config_path = config_path
        self._registry = registry
        self._audit_log = audit_log
        self._on_config_updated = on_config_updated

    def reload(self) -> CronWatcherConfig:
        """Load config, sync registry, emit audit events, return new config."""
        config = load_config(self._config_path)
        diff = self._registry.sync(config.jobs)

        self._audit_log.record(**audit_events.config_reloaded(self._config_path))

        for job in diff.added:
            logger.info("Job added: %s", job.name)
            self._audit_log.record(**audit_events.job_added(job.name))

        for name in diff.removed:
            logger.info("Job removed: %s", name)
            self._audit_log.record(**audit_events.job_removed(name))

        if self._on_config_updated:
            self._on_config_updated(config)

        return config
