"""Formats Report objects into human-readable text or HTML."""

from cronwatcher.reporter import Report, JobSummary


class TextFormatter:
    """Renders a Report as plain text."""

    def format(self, report: Report) -> str:
        lines = [
            f"CronWatcher Report — {report.generated_at.strftime('%Y-%m-%d %H:%M')} UTC",
            f"Period: last {report.period_hours}h | Jobs tracked: {report.total_jobs}",
            "-" * 60,
        ]
        for s in report.summaries:
            lines.append(self._format_summary(s))
        if report.jobs_with_failures:
            lines.append("-" * 60)
            names = ", ".join(s.job_name for s in report.jobs_with_failures)
            lines.append(f"⚠ Jobs with failures: {names}")
        return "\n".join(lines)

    def _format_summary(self, s: JobSummary) -> str:
        avg = f"{s.avg_duration_seconds:.1f}s" if s.avg_duration_seconds is not None else "N/A"
        last = s.last_run_at.strftime("%Y-%m-%d %H:%M") if s.last_run_at else "never"
        return (
            f"{s.job_name}: runs={s.total_runs} ok={s.successful_runs} "
            f"fail={s.failed_runs} success={s.success_rate:.0f}% "
            f"avg={avg} last={last} [{s.last_status or 'N/A'}]"
        )


class HtmlFormatter:
    """Renders a Report as a simple HTML table."""

    def format(self, report: Report) -> str:
        rows = "".join(self._row(s) for s in report.summaries)
        return f"""\
<html><body>
<h2>CronWatcher Report &mdash; {report.generated_at.strftime('%Y-%m-%d %H:%M')} UTC</h2>
<p>Period: last {report.period_hours}h &nbsp;|&nbsp; Jobs tracked: {report.total_jobs}</p>
<table border="1" cellpadding="4" cellspacing="0">
  <tr>
    <th>Job</th><th>Runs</th><th>OK</th><th>Fail</th>
    <th>Success %</th><th>Avg Duration</th><th>Last Run</th><th>Last Status</th>
  </tr>
  {rows}
</table>
</body></html>"""

    def _row(self, s: JobSummary) -> str:
        avg = f"{s.avg_duration_seconds:.1f}s" if s.avg_duration_seconds is not None else "N/A"
        last = s.last_run_at.strftime("%Y-%m-%d %H:%M") if s.last_run_at else "never"
        color = "#fdd" if s.failed_runs > 0 else "#dfd"
        return (
            f'<tr style="background:{color}">'
            f"<td>{s.job_name}</td><td>{s.total_runs}</td><td>{s.successful_runs}</td>"
            f"<td>{s.failed_runs}</td><td>{s.success_rate:.0f}%</td>"
            f"<td>{avg}</td><td>{last}</td><td>{s.last_status or 'N/A'}</td></tr>"
        )
