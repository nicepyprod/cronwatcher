"""Tests for cronwatcher configuration loader."""

import json
import os
import tempfile
import pytest

from cronwatcher.config import load_config, CronWatcherConfig, JobConfig, AlertConfig


def write_config(data: dict) -> str:
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(data, tmp)
    tmp.close()
    return tmp.name


def test_load_defaults_when_file_missing():
    cfg = load_config("/nonexistent/path/config.json")
    assert isinstance(cfg, CronWatcherConfig)
    assert cfg.check_interval_seconds == 60
    assert cfg.jobs == []


def test_load_jobs_from_file():
    data = {
        "jobs": [
            {"name": "backup", "schedule": "0 2 * * *", "timeout_seconds": 1800},
            {"name": "report", "schedule": "0 8 * * 1"},
        ]
    }
    path = write_config(data)
    try:
        cfg = load_config(path)
        assert len(cfg.jobs) == 2
        assert cfg.jobs[0].name == "backup"
        assert cfg.jobs[0].timeout_seconds == 1800
        assert cfg.jobs[1].timeout_seconds == 3600  # default
    finally:
        os.unlink(path)


def test_load_alert_config():
    data = {
        "alerts": {
            "email": "ops@example.com",
            "webhook_url": "https://hooks.example.com/alert",
        }
    }
    path = write_config(data)
    try:
        cfg = load_config(path)
        assert cfg.alerts.email == "ops@example.com"
        assert cfg.alerts.webhook_url == "https://hooks.example.com/alert"
        assert cfg.alerts.slack_channel is None
    finally:
        os.unlink(path)


def test_load_custom_intervals():
    data = {"check_interval_seconds": 30, "log_file": "/tmp/cw.log"}
    path = write_config(data)
    try:
        cfg = load_config(path)
        assert cfg.check_interval_seconds == 30
        assert cfg.log_file == "/tmp/cw.log"
    finally:
        os.unlink(path)


def test_env_var_config_path(monkeypatch, tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"check_interval_seconds": 120}))
    monkeypatch.setenv("CRONWATCHER_CONFIG", str(config_file))
    cfg = load_config()
    assert cfg.check_interval_seconds == 120
