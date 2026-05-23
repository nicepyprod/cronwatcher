"""Prometheus-style text metrics exporter for cronwatcher."""

from __future__ import annotations

from typing import List

from cronwatcher.metrics import MetricsCollector
from cronwatcher.rate_limiter import AlertRateLimiter


class MetricsExporter:
    """Renders collected metrics and rate-limiter state as plain text."""

    def __init__(
        self,
        collector: MetricsCollector,
        rate_limiter: AlertRateLimiter | None = None,
    ) -> None:
        self._collector = collector
        self._limiter = rate_limiter

    def export(self) -> str:
        """Return a Prometheus-compatible plain-text metrics page."""
        lines: List[str] = []
        metrics_map = self._collector.collect()

        for job_name, metrics in metrics_map.items():
            safe = job_name.replace("-", "_").replace(" ", "_")
            d = metrics.as_dict()
            lines.append(
                f'cronwatcher_avg_duration_seconds{{job="{job_name}"}} '
                f'{d["avg_duration_seconds"]:.4f}'
            )
            lines.append(
                f'cronwatcher_success_rate{{job="{job_name}"}} '
                f'{d["success_rate"]:.4f}'
            )
            lines.append(
                f'cronwatcher_total_runs{{job="{job_name}"}} '
                f'{d["total_runs"]}'
            )
            lines.append(
                f'cronwatcher_failed_runs{{job="{job_name}"}} '
                f'{d["failed_runs"]}'
            )
            _ = safe  # suppress unused warning

        if self._limiter is not None:
            lines.append("# rate_limiter entries present")

        return "\n".join(lines) + "\n" if lines else ""

    def export_json(self) -> dict:
        """Return metrics as a plain dict for JSON serialisation."""
        metrics_map = self._collector.collect()
        return {
            job_name: metrics.as_dict()
            for job_name, metrics in metrics_map.items()
        }
