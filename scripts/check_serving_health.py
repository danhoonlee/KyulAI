#!/usr/bin/env python3
"""Watch the serving units and the public endpoints, and report state changes.

Runs from a systemd timer. Deliberately uses only the standard library and the
system interpreter: if the project venv breaks, this still has to run.

systemd's OnFailure would not have caught the outage that prompted this. The
injection unit was stopped cleanly by SIGTERM and stayed down for ten hours
without ever entering a failed state, so what matters is whether the thing is
*running*, not whether it crashed.

Alerts fire on transition — up to down, and back — rather than on every run, so
a healthy host is silent. A target that stays down is re-reported every
REPEAT_AFTER checks so a long outage cannot go quiet.

Set IMPERIALAX_ALERT_SLACK_WEBHOOK to post to Slack. Without it the script still
records state and writes the report to stdout, which systemd captures.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

UNITS = (
    "imperialax-laminate",
    "imperialax-injection",
    "imperialax-cloudflared",
    "imperialax-redis",
    "cafedecafe-cloudflared",
    "cafedecafe-nangman",
    "ds-wedding",
)

ENDPOINTS = (
    "https://ai.imperialax.com/health",
    "https://laminate.imperialax.com/health",
    "https://injection.imperialax.com/health",
    "https://dd.imperialax.com/health",
    "https://app.imperialax.com/health",
)

STATE_PATH = Path.home() / ".local/state/imperialax/serving-health.json"
HTTP_TIMEOUT_S = 20
REPEAT_AFTER = 6  # at a 5-minute timer this re-reports a stuck outage every 30 min


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def check_unit(unit: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", unit],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"systemctl failed: {exc}"
    state = result.stdout.strip() or result.stderr.strip() or "unknown"
    return state == "active", state


def check_endpoint(url: str) -> tuple[bool, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "imperialax-health-check/1"})
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_S) as response:
            code = response.getcode()
            return code == 200, str(code)
    except urllib.error.HTTPError as exc:
        return False, str(exc.code)
    except Exception as exc:  # noqa: BLE001 - any failure to reach it is a failure
        return False, type(exc).__name__


def load_state() -> dict[str, dict[str, object]]:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(state: dict[str, dict[str, object]]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(STATE_PATH)


def post_to_slack(text: str) -> str:
    webhook = os.environ.get("IMPERIALAX_ALERT_SLACK_WEBHOOK", "").strip()
    if not webhook:
        return "no webhook configured"
    payload = json.dumps({"text": text}).encode("utf-8")
    request = urllib.request.Request(
        webhook, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_S) as response:
            return f"slack {response.getcode()}"
    except Exception as exc:  # noqa: BLE001 - never let alerting break the check
        return f"slack failed: {exc}"


def main() -> int:
    targets: list[tuple[str, str, bool, str]] = []
    for unit in UNITS:
        healthy, detail = check_unit(unit)
        targets.append((f"unit:{unit}", unit, healthy, detail))
    for url in ENDPOINTS:
        healthy, detail = check_endpoint(url)
        targets.append((f"http:{url}", url.split("//", 1)[-1].split("/", 1)[0], healthy, detail))

    previous = load_state()
    current: dict[str, dict[str, object]] = {}
    recovered: list[str] = []
    newly_down: list[str] = []
    still_down: list[str] = []

    for key, label, healthy, detail in targets:
        was = previous.get(key, {})
        was_healthy = bool(was.get("healthy", True))
        failures = 0 if healthy else int(was.get("failures", 0)) + 1
        current[key] = {
            "healthy": healthy,
            "detail": detail,
            "failures": failures,
            "checked_at": _now(),
        }
        if healthy and not was_healthy:
            recovered.append(f"{label} ({detail})")
        elif not healthy and was_healthy:
            newly_down.append(f"{label} -> {detail}")
        elif not healthy and failures % REPEAT_AFTER == 0:
            still_down.append(f"{label} -> {detail} (down for {failures} checks)")

    save_state(current)

    down_now = [key for key, value in current.items() if not value["healthy"]]
    summary = f"{len(targets) - len(down_now)}/{len(targets)} healthy"

    lines: list[str] = []
    if newly_down:
        lines.append(":rotating_light: *ImperialAX serving is down*")
        lines.extend(f"• {item}" for item in newly_down)
    if still_down:
        lines.append(":warning: *ImperialAX serving still down*")
        lines.extend(f"• {item}" for item in still_down)
    if recovered:
        lines.append(":white_check_mark: *ImperialAX serving recovered*")
        lines.extend(f"• {item}" for item in recovered)

    if lines:
        lines.append(f"_{summary} · {_now()}_")
        message = "\n".join(lines)
        print(message)
        print(post_to_slack(message))
    else:
        print(f"{_now()} {summary}")

    return 1 if down_now else 0


if __name__ == "__main__":
    sys.exit(main())
