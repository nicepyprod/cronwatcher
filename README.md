# cronwatcher

A daemon that monitors cron job execution, logs durations, and sends alerts on failures or missed runs.

## Installation

```bash
pip install cronwatcher
```

Or install from source:

```bash
git clone https://github.com/youruser/cronwatcher.git && cd cronwatcher && pip install .
```

## Usage

Start the daemon:

```bash
cronwatcher start --config /etc/cronwatcher/config.yaml
```

Example `config.yaml`:

```yaml
jobs:
  - name: daily-backup
    schedule: "0 2 * * *"
    command: /usr/local/bin/backup.sh
    timeout: 3600
    alert_on_failure: true
    alert_on_missed: true

alerts:
  email: ops@example.com
  slack_webhook: https://hooks.slack.com/services/xxx/yyy/zzz

log:
  path: /var/log/cronwatcher.log
  level: info
```

Stop the daemon:

```bash
cronwatcher stop
```

View job execution history:

```bash
cronwatcher status
```

## How It Works

cronwatcher wraps your cron jobs, records start/end times and exit codes, and compares actual run times against the defined schedule. If a job fails or is missed within a configurable window, alerts are dispatched via email or Slack.

## Requirements

- Python 3.8+
- Linux / macOS

## License

This project is licensed under the [MIT License](LICENSE).