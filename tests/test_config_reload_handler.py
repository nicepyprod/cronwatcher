"""Tests for ConfigReloadHandler."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.audit_log import AuditLog
from cronwatcher.config import JobConfig
from cronwatcher.config_reload_handler import ConfigReloadHandler
from cronwatcher.job_registry import JobRegistry


YAML_CONTENT = """
jobs:
  - name: backup
    schedule: "0 2 * * *"
    command: /usr/bin/backup.sh
  - name: cleanup
    schedule: "0 3 * * *"
    command: /usr/bin/cleanup.sh
"""


@pytest.fixture
def config_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(YAML_CONTENT)
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def audit_log():
    return AuditLog(":memory:")


@pytest.fixture
def registry():
    return JobRegistry()


def test_reload_returns_config(config_file, registry, audit_log):
    handler = ConfigReloadHandler(config_file, registry, audit_log)
    config = handler.reload()
    assert len(config.jobs) == 2
    assert {j.name for j in config.jobs} == {"backup", "cleanup"}


def test_reload_syncs_registry(config_file, registry, audit_log):
    handler = ConfigReloadHandler(config_file, registry, audit_log)
    handler.reload()
    assert set(registry.names()) == {"backup", "cleanup"}


def test_reload_emits_audit_events(config_file, registry, audit_log):
    handler = ConfigReloadHandler(config_file, registry, audit_log)
    handler.reload()
    entries = audit_log.recent(limit=10)
    event_types = {e.event_type for e in entries}
    assert "config_reloaded" in event_types


def test_reload_calls_on_config_updated(config_file, registry, audit_log):
    callback = MagicMock()
    handler = ConfigReloadHandler(config_file, registry, audit_log, on_config_updated=callback)
    config = handler.reload()
    callback.assert_called_once_with(config)


def test_added_jobs_logged_in_audit(config_file, registry, audit_log):
    handler = ConfigReloadHandler(config_file, registry, audit_log)
    handler.reload()
    entries = audit_log.recent(limit=20)
    event_types = [e.event_type for e in entries]
    assert "job_added" in event_types
