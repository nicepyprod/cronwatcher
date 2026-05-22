"""Configuration loader for cronwatcher daemon."""

import os
import json
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class JobConfig:
    name: str
    schedule: str
    timeout_seconds: int = 3600
    alert_on_failure: bool = True
    alert_on_missed: bool = True


@dataclass
class AlertConfig:
    email: Optional[str] = None
    webhook_url: Optional[str] = None
    slack_channel: Optional[str] = None


@dataclass
class CronWatcherConfig:
    log_file: str = "/var/log/cronwatcher/cronwatcher.log"
    db_path: str = "/var/lib/cronwatcher/jobs.db"
    check_interval_seconds: int = 60
    jobs: List[JobConfig] = field(default_factory=list)
    alerts: AlertConfig = field(default_factory=AlertConfig)


def load_config(path: Optional[str] = None) -> CronWatcherConfig:
    """Load configuration from a JSON file or environment variables."""
    config_path = path or os.environ.get("CRONWATCHER_CONFIG", "/etc/cronwatcher/config.json")

    if not os.path.exists(config_path):
        return CronWatcherConfig()

    with open(config_path, "r") as f:
        raw = json.load(f)

    jobs = [
        JobConfig(
            name=j["name"],
            schedule=j["schedule"],
            timeout_seconds=j.get("timeout_seconds", 3600),
            alert_on_failure=j.get("alert_on_failure", True),
            alert_on_missed=j.get("alert_on_missed", True),
        )
        for j in raw.get("jobs", [])
    ]

    alert_raw = raw.get("alerts", {})
    alerts = AlertConfig(
        email=alert_raw.get("email"),
        webhook_url=alert_raw.get("webhook_url"),
        slack_channel=alert_raw.get("slack_channel"),
    )

    return CronWatcherConfig(
        log_file=raw.get("log_file", CronWatcherConfig.log_file),
        db_path=raw.get("db_path", CronWatcherConfig.db_path),
        check_interval_seconds=raw.get("check_interval_seconds", 60),
        jobs=jobs,
        alerts=alerts,
    )
