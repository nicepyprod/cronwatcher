"""Tests for CronWatcher daemon logic."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.config import AlertConfig, CronWatcherConfig, JobConfig
from cronwatcher.watcher import CronWatcher


@pytest.fixture()
def config() -> CronWatcherConfig:
    return CronWatcherConfig(
        jobs=[JobConfig(name="nightly", schedule="0 2 * * *")],
        alert=AlertConfig(enabled=False),
        check_interval_seconds=60,
        grace_seconds=120,
    )


@pytest.fixture()
def store() -> MagicMock:
    return MagicMock()


class TestCheckOnce:
    def test_no_alert_when_no_missed_jobs(self, config: CronWatcherConfig, store: MagicMock) -> None:
        watcher = CronWatcher(config, store)
        with patch.object(watcher._detector, "check_all", return_value=[]) as mock_check, \
             patch.object(watcher._sender, "send") as mock_send:
            watcher._check_once()
            mock_check.assert_called_once()
            mock_send.assert_not_called()

    def test_alert_sent_for_each_missed_job(self, config: CronWatcherConfig, store: MagicMock) -> None:
        watcher = CronWatcher(config, store)
        with patch.object(watcher._detector, "check_all", return_value=["nightly"]), \
             patch.object(watcher._sender, "send", return_value=True) as mock_send:
            watcher._check_once()
            assert mock_send.call_count == 1
            event = mock_send.call_args[0][0]
            assert event.job_name == "nightly"
            assert event.status == "missed"

    def test_alert_failure_logged_but_no_exception(self, config: CronWatcherConfig, store: MagicMock) -> None:
        watcher = CronWatcher(config, store)
        with patch.object(watcher._detector, "check_all", return_value=["nightly"]), \
             patch.object(watcher._sender, "send", return_value=False):
            # Should not raise even if send returns False
            watcher._check_once()

    def test_multiple_missed_jobs_each_get_alert(self, config: CronWatcherConfig, store: MagicMock) -> None:
        multi_config = CronWatcherConfig(
            jobs=[
                JobConfig(name="job_a", schedule="* * * * *"),
                JobConfig(name="job_b", schedule="* * * * *"),
            ],
            alert=AlertConfig(enabled=False),
            check_interval_seconds=60,
            grace_seconds=0,
        )
        watcher = CronWatcher(multi_config, store)
        with patch.object(watcher._detector, "check_all", return_value=["job_a", "job_b"]), \
             patch.object(watcher._sender, "send", return_value=True) as mock_send:
            watcher._check_once()
            assert mock_send.call_count == 2
            names = {call[0][0].job_name for call in mock_send.call_args_list}
            assert names == {"job_a", "job_b"}


class TestStop:
    def test_stop_sets_running_false(self, config: CronWatcherConfig, store: MagicMock) -> None:
        watcher = CronWatcher(config, store)
        watcher._running = True
        watcher.stop()
        assert watcher._running is False
