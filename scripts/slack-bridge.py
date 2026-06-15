#!/usr/bin/env python3
"""Forward KyulAI agent-bus events to Slack.

This script watches .agent-bus/messages.jsonl and .agent-bus/tasks.jsonl, then
sends new events to a Slack channel through an Incoming Webhook. It is an
observer bridge: agents keep coordinating through the local bus, while humans
can watch progress in Slack.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any


BUS_DIR = Path(os.environ.get("AGENT_BUS_DIR", ".agent-bus"))
MESSAGES_FILE = BUS_DIR / "messages.jsonl"
TASKS_FILE = BUS_DIR / "tasks.jsonl"
STATE_FILE = BUS_DIR / "slack-bridge-state.json"
MAX_SLACK_LENGTH = 38000


def ensure_bus() -> None:
    BUS_DIR.mkdir(parents=True, exist_ok=True)
    MESSAGES_FILE.touch(exist_ok=True)
    TASKS_FILE.touch(exist_ok=True)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    ensure_bus()
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_state(since: str) -> dict[str, int]:
    ensure_bus()
    if STATE_FILE.exists():
        with STATE_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    if since == "beginning":
        return {"messages": 0, "tasks": 0}
    return {
        "messages": len(read_jsonl(MESSAGES_FILE)),
        "tasks": len(read_jsonl(TASKS_FILE)),
    }


def save_state(state: dict[str, int]) -> None:
    ensure_bus()
    with STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")


def truncate(text: str) -> str:
    if len(text) <= MAX_SLACK_LENGTH:
        return text
    return text[: MAX_SLACK_LENGTH - 80] + "\n\n[truncated by KyulAI Slack bridge]"


def send_slack(text: str, dry_run: bool) -> None:
    if dry_run:
        print("--- slack dry run ---")
        print(text)
        return

    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        raise SystemExit("SLACK_WEBHOOK_URL must be set")

    body = json.dumps({"text": truncate(text)}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        response.read()


def format_message(event: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"*KyulAI message* `{event.get('from')}` -> `{event.get('to')}`",
            f"*Topic:* {event.get('topic', 'general')}",
            f"*Subject:* {event.get('subject', '')}",
            "",
            str(event.get("body", "")),
            "",
            f"*At:* {event.get('created_at')}",
            f"*ID:* `{event.get('id')}`",
        ]
    )


def format_task(event: dict[str, Any]) -> str:
    if event.get("event") == "created":
        lines = [
            f"*KyulAI task created* `{event.get('from')}` -> `{event.get('to')}`",
            f"*Title:* {event.get('title', '')}",
            f"*Status:* `{event.get('status', 'pending')}`",
            "",
            str(event.get("body", "")),
            "",
            f"*At:* {event.get('created_at')}",
            f"*ID:* `{event.get('id')}`",
        ]
    else:
        lines = [
            f"*KyulAI task updated* `{event.get('id')}`",
            f"*By:* `{event.get('by')}`",
            f"*To:* `{event.get('to')}`",
            f"*Status:* `{event.get('status')}`",
            f"*Note:* {event.get('note', '')}",
            "",
            f"*At:* {event.get('updated_at')}",
        ]
    return "\n".join(lines)


def forward_new_events(state: dict[str, int], dry_run: bool) -> dict[str, int]:
    messages = read_jsonl(MESSAGES_FILE)
    tasks = read_jsonl(TASKS_FILE)

    for event in messages[state.get("messages", 0) :]:
        send_slack(format_message(event), dry_run=dry_run)

    for event in tasks[state.get("tasks", 0) :]:
        send_slack(format_task(event), dry_run=dry_run)

    return {"messages": len(messages), "tasks": len(tasks)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Forward KyulAI agent-bus events to Slack")
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    parser.add_argument("--once", action="store_true", help="process pending events once and exit")
    parser.add_argument("--dry-run", action="store_true", help="print messages instead of sending to Slack")
    parser.add_argument(
        "--since",
        choices=["now", "beginning"],
        default="now",
        help="initial event position when no bridge state exists",
    )
    parser.add_argument("--reset-state", action="store_true", help="remove saved bridge offsets before starting")
    parser.add_argument("--send-test", action="store_true", help="send a Slack test message and exit")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    ensure_bus()

    if args.reset_state and STATE_FILE.exists():
        STATE_FILE.unlink()

    if args.send_test:
        send_slack(
            "KyulAI Slack bridge is connected. New agent-bus messages and tasks will appear here.",
            dry_run=args.dry_run,
        )
        return

    state = load_state(args.since)
    save_state(state)

    while True:
        try:
            state = forward_new_events(state, dry_run=args.dry_run)
            save_state(state)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            print(f"slack bridge error: {exc}", file=sys.stderr)
        if args.once:
            return
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
