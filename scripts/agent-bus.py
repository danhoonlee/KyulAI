#!/usr/bin/env python3
"""Local message and task bus for KyulAI agent teams.

The bus is intentionally simple: append-only JSONL files in .agent-bus/.
That makes it easy for multiple terminal agents to coordinate without needing
Slack, Discord, Telegram, or a database.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any


ROOT = Path(os.environ.get("AGENT_BUS_DIR", ".agent-bus"))
MESSAGES_FILE = ROOT / "messages.jsonl"
TASKS_FILE = ROOT / "tasks.jsonl"

TASK_STATUSES = {"pending", "in_progress", "blocked", "done", "canceled"}


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{int(time.time())}_{uuid.uuid4().hex[:8]}"


def ensure_bus() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    MESSAGES_FILE.touch(exist_ok=True)
    TASKS_FILE.touch(exist_ok=True)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    ensure_bus()
    with path.open("a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        f.flush()
        fcntl.flock(f, fcntl.LOCK_UN)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    ensure_bus()
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def send_webhook_json(url: str, payload: dict[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        response.read()


def send_telegram(text: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("telegram notification skipped: TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not set", file=sys.stderr)
        return

    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    request = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(request, timeout=10) as response:
        response.read()


def notify(target: str, text: str) -> None:
    targets = ["slack", "discord", "telegram"] if target == "all" else [target]
    for item in targets:
        try:
            if item == "none":
                continue
            if item == "slack":
                url = os.environ.get("SLACK_WEBHOOK_URL")
                if not url:
                    print("slack notification skipped: SLACK_WEBHOOK_URL not set", file=sys.stderr)
                    continue
                send_webhook_json(url, {"text": text})
            elif item == "discord":
                url = os.environ.get("DISCORD_WEBHOOK_URL")
                if not url:
                    print("discord notification skipped: DISCORD_WEBHOOK_URL not set", file=sys.stderr)
                    continue
                send_webhook_json(url, {"content": text})
            elif item == "telegram":
                send_telegram(text)
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"{item} notification failed: {exc}", file=sys.stderr)


def command_post(args: argparse.Namespace) -> None:
    message = {
        "id": new_id("msg"),
        "type": "message",
        "created_at": now(),
        "from": args.sender,
        "to": args.recipient,
        "topic": args.topic,
        "subject": args.subject,
        "body": args.body,
    }
    append_jsonl(MESSAGES_FILE, message)
    if args.notify != "none":
        notify(args.notify, f"[KyulAI:{args.topic}] {args.sender} -> {args.recipient}: {args.subject}\n{args.body}")
    print_json(message)


def command_inbox(args: argparse.Namespace) -> None:
    messages = read_jsonl(MESSAGES_FILE)
    visible = [
        item
        for item in messages
        if item.get("to") in {args.agent, "all", "*"} or item.get("from") == args.agent
    ]
    print_json(visible[-args.limit :])


def command_task_create(args: argparse.Namespace) -> None:
    event = {
        "event": "created",
        "id": new_id("task"),
        "created_at": now(),
        "updated_at": now(),
        "from": args.sender,
        "to": args.recipient,
        "title": args.title,
        "body": args.body,
        "status": "pending",
        "depends_on": args.depends_on or [],
        "history": [{"at": now(), "by": args.sender, "status": "pending", "note": "created"}],
    }
    append_jsonl(TASKS_FILE, event)
    if args.notify != "none":
        notify(args.notify, f"[KyulAI task] {args.sender} -> {args.recipient}: {args.title}\n{args.body}")
    print_json(event)


def reconstruct_tasks() -> dict[str, dict[str, Any]]:
    tasks: dict[str, dict[str, Any]] = {}
    for event in read_jsonl(TASKS_FILE):
        task_id = event["id"]
        if event.get("event") == "created":
            tasks[task_id] = dict(event)
            continue
        if task_id not in tasks:
            continue
        tasks[task_id].update(
            {
                "updated_at": event["updated_at"],
                "status": event["status"],
                "to": event.get("to", tasks[task_id].get("to")),
            }
        )
        tasks[task_id].setdefault("history", []).append(
            {
                "at": event["updated_at"],
                "by": event["by"],
                "status": event["status"],
                "note": event.get("note", ""),
            }
        )
    return tasks


def command_task_list(args: argparse.Namespace) -> None:
    tasks = list(reconstruct_tasks().values())
    if args.agent:
        tasks = [task for task in tasks if task.get("to") in {args.agent, "all", "*"} or task.get("from") == args.agent]
    if args.status:
        tasks = [task for task in tasks if task.get("status") == args.status]
    print_json(tasks[-args.limit :])


def command_task_update(args: argparse.Namespace) -> None:
    if args.status not in TASK_STATUSES:
        raise SystemExit(f"invalid status: {args.status}")

    tasks = reconstruct_tasks()
    if args.task_id not in tasks:
        raise SystemExit(f"unknown task id: {args.task_id}")

    event = {
        "event": "updated",
        "id": args.task_id,
        "updated_at": now(),
        "by": args.by,
        "to": args.to or tasks[args.task_id].get("to"),
        "status": args.status,
        "note": args.note or "",
    }
    append_jsonl(TASKS_FILE, event)
    print_json(reconstruct_tasks()[args.task_id])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="KyulAI local agent message bus")
    subcommands = parser.add_subparsers(dest="command", required=True)

    post = subcommands.add_parser("post", help="send a message")
    post.add_argument("--from", dest="sender", required=True)
    post.add_argument("--to", dest="recipient", required=True)
    post.add_argument("--topic", default="general")
    post.add_argument("--subject", required=True)
    post.add_argument("--body", required=True)
    post.add_argument("--notify", choices=["none", "slack", "discord", "telegram", "all"], default="none")
    post.set_defaults(func=command_post)

    inbox = subcommands.add_parser("inbox", help="read messages visible to an agent")
    inbox.add_argument("--agent", required=True)
    inbox.add_argument("--limit", type=int, default=20)
    inbox.set_defaults(func=command_inbox)

    task = subcommands.add_parser("task", help="manage tasks")
    task_commands = task.add_subparsers(dest="task_command", required=True)

    create = task_commands.add_parser("create", help="create a task")
    create.add_argument("--from", dest="sender", required=True)
    create.add_argument("--to", dest="recipient", required=True)
    create.add_argument("--title", required=True)
    create.add_argument("--body", required=True)
    create.add_argument("--depends-on", action="append", default=[])
    create.add_argument("--notify", choices=["none", "slack", "discord", "telegram", "all"], default="none")
    create.set_defaults(func=command_task_create)

    list_tasks = task_commands.add_parser("list", help="list tasks")
    list_tasks.add_argument("--agent")
    list_tasks.add_argument("--status", choices=sorted(TASK_STATUSES))
    list_tasks.add_argument("--limit", type=int, default=50)
    list_tasks.set_defaults(func=command_task_list)

    update = task_commands.add_parser("update", help="update task status")
    update.add_argument("--id", dest="task_id", required=True)
    update.add_argument("--status", required=True, choices=sorted(TASK_STATUSES))
    update.add_argument("--by", required=True)
    update.add_argument("--to")
    update.add_argument("--note")
    update.set_defaults(func=command_task_update)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
