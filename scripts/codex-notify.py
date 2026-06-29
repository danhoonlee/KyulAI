#!/usr/bin/env python3
"""Send Codex work notifications to Telegram and Slack.

This is intentionally independent from the local agent bus. Use it when Codex
needs to nudge the user about approval prompts, long-running work, completion,
or failures while the user is away from the computer.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


EVENT_TITLES = {
    "approval": "Codex approval needed",
    "complete": "Codex task complete",
    "failed": "Codex task failed",
    "info": "Codex update",
    "test": "Codex notification test",
}

CHANNELS = ("telegram", "slack")
MAX_SLACK_LENGTH = 38000
MAX_TELEGRAM_LENGTH = 3900


def configured_channels() -> list[str]:
    channels: list[str] = []
    if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
        channels.append("telegram")
    if os.environ.get("SLACK_WEBHOOK_URL"):
        channels.append("slack")
    return channels


def resolve_channels(target: str) -> list[str]:
    if target == "auto":
        return configured_channels()
    if target == "all":
        return list(CHANNELS)
    return [target]


def truncate(text: str, limit: int, label: str) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - len(label) - 2] + "\n" + label


def send_json_webhook(url: str, payload: dict[str, Any], timeout: float) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        response.read()


def send_slack(text: str, timeout: float) -> None:
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        raise RuntimeError("SLACK_WEBHOOK_URL is not set")
    send_json_webhook(
        url,
        {"text": truncate(text, MAX_SLACK_LENGTH, "[truncated by codex-notify]")},
        timeout=timeout,
    )


def send_telegram(text: str, timeout: float) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")

    data = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": truncate(text, MAX_TELEGRAM_LENGTH, "[truncated by codex-notify]"),
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=data,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        response.read()


def read_message(args: argparse.Namespace) -> str:
    parts: list[str] = []
    if args.message:
        parts.append(args.message)
    if args.stdin:
        stdin_text = sys.stdin.read().strip()
        if stdin_text:
            parts.append(stdin_text)
    return "\n\n".join(parts).strip()


def build_text(args: argparse.Namespace) -> str:
    title = args.title or EVENT_TITLES[args.event]
    message = read_message(args)
    project = args.project or Path.cwd().name
    host = socket.gethostname()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S %Z")

    lines = [
        f"[{title}]",
        f"Event: {args.event}",
        f"Project: {project}",
        f"Host: {host}",
        f"Time: {timestamp}",
    ]
    if args.cwd:
        lines.append(f"Path: {Path.cwd()}")
    if message:
        lines.extend(["", message])
    return "\n".join(lines)


def send(targets: list[str], text: str, timeout: float, dry_run: bool) -> dict[str, str]:
    results: dict[str, str] = {}
    for target in targets:
        if target not in CHANNELS:
            results[target] = "unsupported"
            continue
        if dry_run:
            results[target] = "dry-run"
            continue
        try:
            if target == "telegram":
                send_telegram(text, timeout=timeout)
            elif target == "slack":
                send_slack(text, timeout=timeout)
            results[target] = "sent"
        except (RuntimeError, TimeoutError, urllib.error.URLError) as exc:
            results[target] = f"failed: {exc}"
    return results


def print_status() -> None:
    status = {
        "configured_channels": configured_channels(),
        "telegram": bool(os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID")),
        "slack": bool(os.environ.get("SLACK_WEBHOOK_URL")),
        "env_required": {
            "telegram": ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"],
            "slack": ["SLACK_WEBHOOK_URL"],
        },
    }
    print(json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send Codex notifications to Telegram/Slack")
    parser.add_argument(
        "event",
        choices=sorted(EVENT_TITLES),
        nargs="?",
        default="info",
        help="notification event type",
    )
    parser.add_argument("--title", help="override notification title")
    parser.add_argument("--message", "-m", help="notification body")
    parser.add_argument("--stdin", action="store_true", help="append stdin to the message body")
    parser.add_argument("--project", help="project name shown in the notification")
    parser.add_argument("--cwd", action="store_true", help="include current working directory")
    parser.add_argument(
        "--channel",
        choices=["auto", "all", "telegram", "slack"],
        default="auto",
        help="where to send the notification",
    )
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--dry-run", action="store_true", help="print payload/results without sending")
    parser.add_argument("--status", action="store_true", help="show configured notification channels and exit")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero when no channel is configured or a send fails",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.status:
        print_status()
        return 0

    text = build_text(args)
    targets = resolve_channels(args.channel)
    if args.dry_run and not targets:
        targets = list(CHANNELS)
    if not targets:
        print("codex-notify: no configured channels found", file=sys.stderr)
        if args.strict:
            return 2
        return 0

    results = send(targets, text, timeout=args.timeout, dry_run=args.dry_run)
    if args.dry_run:
        print("--- notification payload ---")
        print(text)
    print(json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True))

    if args.strict and any(not value.startswith(("sent", "dry-run")) for value in results.values()):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
