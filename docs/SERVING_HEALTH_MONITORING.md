# Serving health monitoring

A five-minute check over the serving units and the public endpoints, reporting
only when something changes.

## Why polling, and not `OnFailure`

The outage that prompted this was `imperialax-injection` stopped cleanly by
SIGTERM at 2026-08-31 00:35 and left down for ten hours, with
`injection.imperialax.com` returning 502 the whole time. The unit never entered
a failed state, so `OnFailure=` would never have fired. What matters is whether
the service is *running*, not whether it crashed — so the check asks
`systemctl is-active` and requests the public URL.

It checks both because they fail independently: a unit can be active while the
Cloudflare tunnel is down, and the tunnel can be up while the app is not.

## What it watches

Units: `imperialax-laminate`, `imperialax-injection`, `imperialax-cloudflared`,
`imperialax-redis`, `cafedecafe-cloudflared`, `cafedecafe-nangman`,
`ds-wedding`.

Endpoints: `/health` on ai, laminate, injection, dd and app `.imperialax.com`.

## Behaviour

- Alerts on **transition** only, so a healthy host is silent.
- A target that stays down is re-reported every 6 checks — about every 30
  minutes — so a long outage cannot go quiet.
- Recovery is reported too.
- Exit code is 1 while anything is down. The unit lists `SuccessExitStatus=0 1`
  so that does not mark it failed; the script has already reported the problem
  and a failed unit would only add noise.

## Files

| Path | Role |
|---|---|
| `scripts/check_serving_health.py` | The check. Standard library and `/usr/bin/python3` only, so it survives a broken project venv. |
| `infrastructure/systemd-user/imperialax-health-check.{service,timer}` | Timer definition, installed into `~/.config/systemd/user/`. |
| `~/.config/imperialax/alerts.env` | Holds `IMPERIALAX_ALERT_SLACK_WEBHOOK`. Mode 600, outside the repository. |
| `~/.local/state/imperialax/serving-health.json` | Last known state per target, which is what makes transition detection possible. |
| `logs/imperialax-health-check.log` | Every run, including the quiet ones. Gitignored. |

## Enabling Slack alerts

Create an incoming webhook at https://api.slack.com/apps → Incoming Webhooks,
pointed at `#imperialax-dev`, then put it in `~/.config/imperialax/alerts.env`:

```
IMPERIALAX_ALERT_SLACK_WEBHOOK=https://hooks.slack.com/services/...
```

No restart is needed; the next timer run picks it up. Until then the check still
runs and records state — it just prints `no webhook configured` instead of
posting.

## Operating it

```bash
systemctl --user list-timers imperialax-health-check   # when it next runs
systemctl --user start imperialax-health-check.service # run it now
tail -f logs/imperialax-health-check.log               # what it saw
python3 scripts/check_serving_health.py                # run by hand
```

To verify it still detects an outage, stop a unit and run the check by hand; it
should report the unit and its endpoint, stay quiet on the next run, and report
the recovery when the unit is started again.
