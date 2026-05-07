"""Slack Slash Command endpoint for KyulAI agent control."""

from __future__ import annotations

import hmac
import hashlib
import json
import os
import time
import urllib.parse
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse


router = APIRouter(prefix="/slack", tags=["slack"])

PROJECT_ROOT = Path(__file__).resolve().parents[4]
BUS_DIR = Path(os.environ.get("AGENT_BUS_DIR", PROJECT_ROOT / ".agent-bus"))
MESSAGES_FILE = BUS_DIR / "messages.jsonl"
TASKS_FILE = BUS_DIR / "tasks.jsonl"
TASK_STATUSES = {"pending", "in_progress", "blocked", "done", "canceled"}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _new_id(prefix: str) -> str:
    return f"{prefix}_{int(time.time())}_{uuid.uuid4().hex[:8]}"


def _ensure_bus() -> None:
    BUS_DIR.mkdir(parents=True, exist_ok=True)
    MESSAGES_FILE.touch(exist_ok=True)
    TASKS_FILE.touch(exist_ok=True)


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    _ensure_bus()
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    _ensure_bus()
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _verify_slack_request(request: Request, raw_body: bytes) -> None:
    signing_secret = os.environ.get("SLACK_SIGNING_SECRET")
    if not signing_secret:
        if os.environ.get("SLACK_ALLOW_UNSIGNED_COMMANDS") == "1":
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SLACK_SIGNING_SECRET is not configured on the KyulAI server.",
        )

    timestamp = request.headers.get("x-slack-request-timestamp")
    signature = request.headers.get("x-slack-signature")
    if not timestamp or not signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Slack signature headers.")

    try:
        request_time = int(timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Slack timestamp.") from exc

    if abs(time.time() - request_time) > 60 * 5:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Stale Slack request.")

    base_string = b"v0:" + timestamp.encode("utf-8") + b":" + raw_body
    digest = hmac.new(signing_secret.encode("utf-8"), base_string, hashlib.sha256).hexdigest()
    expected_signature = f"v0={digest}"
    if not hmac.compare_digest(expected_signature, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Slack signature.")


def _verify_allowed_user(form: dict[str, str]) -> None:
    allowed = {
        item.strip()
        for item in os.environ.get("SLACK_ALLOWED_USER_IDS", "").split(",")
        if item.strip()
    }
    if not allowed:
        return
    user_id = form.get("user_id", "")
    if user_id not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This Slack user is not allowed.")


def _slack_response(text: str) -> JSONResponse:
    return JSONResponse({"response_type": "ephemeral", "text": text})


def _parse_form(raw_body: bytes) -> dict[str, str]:
    parsed = urllib.parse.parse_qs(raw_body.decode("utf-8"), keep_blank_values=True)
    return {key: values[0] if values else "" for key, values in parsed.items()}


def _task_create(form: dict[str, str], body: str) -> str:
    if not body:
        return "Usage: `/kyulai task <work request>`"
    event = {
        "event": "created",
        "id": _new_id("task"),
        "created_at": _now(),
        "updated_at": _now(),
        "from": f"slack:{form.get('user_name') or form.get('user_id')}",
        "to": "orchestrator",
        "title": body[:96],
        "body": body,
        "status": "pending",
        "depends_on": [],
        "history": [
            {
                "at": _now(),
                "by": f"slack:{form.get('user_name') or form.get('user_id')}",
                "status": "pending",
                "note": f"created from Slack channel {form.get('channel_name')}",
            }
        ],
        "slack": {
            "team_id": form.get("team_id"),
            "channel_id": form.get("channel_id"),
            "channel_name": form.get("channel_name"),
            "user_id": form.get("user_id"),
            "user_name": form.get("user_name"),
        },
    }
    _append_jsonl(TASKS_FILE, event)
    return f"Task created for `orchestrator`: `{event['id']}`\n{body}"


def _message_create(form: dict[str, str], text: str) -> str:
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return "Usage: `/kyulai msg <agent> <message>`"
    recipient, body = parts
    event = {
        "id": _new_id("msg"),
        "type": "message",
        "created_at": _now(),
        "from": f"slack:{form.get('user_name') or form.get('user_id')}",
        "to": recipient,
        "topic": "slack",
        "subject": f"Slack message from {form.get('user_name') or form.get('user_id')}",
        "body": body,
        "slack": {
            "team_id": form.get("team_id"),
            "channel_id": form.get("channel_id"),
            "channel_name": form.get("channel_name"),
            "user_id": form.get("user_id"),
            "user_name": form.get("user_name"),
        },
    }
    _append_jsonl(MESSAGES_FILE, event)
    return f"Message sent to `{recipient}`: `{event['id']}`"


def _reconstruct_tasks() -> dict[str, dict[str, Any]]:
    tasks: dict[str, dict[str, Any]] = {}
    for event in _read_jsonl(TASKS_FILE):
        task_id = event["id"]
        if event.get("event") == "created":
            tasks[task_id] = dict(event)
            continue
        if task_id not in tasks:
            continue
        tasks[task_id].update(
            {
                "updated_at": event.get("updated_at"),
                "status": event.get("status"),
                "to": event.get("to", tasks[task_id].get("to")),
            }
        )
        tasks[task_id].setdefault("history", []).append(
            {
                "at": event.get("updated_at"),
                "by": event.get("by"),
                "status": event.get("status"),
                "note": event.get("note", ""),
            }
        )
    return tasks


def _status() -> str:
    tasks = list(_reconstruct_tasks().values())
    open_tasks = [task for task in tasks if task.get("status") in TASK_STATUSES - {"done", "canceled"}]
    recent_messages = _read_jsonl(MESSAGES_FILE)[-3:]
    lines = [
        "*KyulAI status*",
        f"Open tasks: `{len(open_tasks)}`",
        f"Total tasks: `{len(tasks)}`",
        f"Recent messages: `{len(recent_messages)}`",
        "",
        "Public apps:",
        "DD: https://dd.cafedecafe.co.kr/",
        "Injection: https://injection.cafedecafe.co.kr/",
    ]
    if open_tasks:
        lines.extend(["", "Recent open tasks:"])
        for task in open_tasks[-5:]:
            lines.append(f"- `{task.get('id')}` `{task.get('status')}` {task.get('title')}")
    return "\n".join(lines)


def _help() -> str:
    return "\n".join(
        [
            "*KyulAI Slack commands*",
            "`/kyulai task <work request>` - create an orchestrator task",
            "`/kyulai msg <agent> <message>` - send a bus message",
            "`/kyulai status` - show recent bus status and app URLs",
            "`/kyulai help` - show this help",
        ]
    )


@router.post("/commands")
async def slack_commands(request: Request) -> JSONResponse:
    raw_body = await request.body()
    _verify_slack_request(request, raw_body)
    form = _parse_form(raw_body)
    _verify_allowed_user(form)

    text = form.get("text", "").strip()
    if not text or text == "help":
        return _slack_response(_help())

    command, _, rest = text.partition(" ")
    command = command.lower()
    rest = rest.strip()

    if command == "task":
        return _slack_response(_task_create(form, rest))
    if command == "msg":
        return _slack_response(_message_create(form, rest))
    if command == "status":
        return _slack_response(_status())

    return _slack_response(f"Unknown KyulAI command: `{command}`\n\n{_help()}")
