# KyulAI Agent Communication

KyulAI agents do not require Telegram, Discord, or Slack to talk to each
other. They need a shared coordination channel. In this project, the default
channel is the local append-only bus under `.agent-bus/`.

## Local Agent Bus

Send a message:

```bash
python3 scripts/agent-bus.py post \
  --from orchestrator \
  --to all \
  --topic status \
  --subject "Starting work" \
  --body "The orchestrator is assigning the next tasks."
```

Create a task:

```bash
python3 scripts/agent-bus.py task create \
  --from orchestrator \
  --to frontend \
  --title "Improve DD UI" \
  --body "Add the requested layout update and report back."
```

Read messages:

```bash
python3 scripts/agent-bus.py inbox --agent orchestrator
```

List tasks:

```bash
python3 scripts/agent-bus.py task list --agent orchestrator
```

## Slack Outbound Bridge

Use this when the user wants to watch agent messages/tasks in Slack.

User setup in Slack:

1. Open <https://api.slack.com/apps>.
2. Create a Slack app in the target workspace.
3. Enable `Incoming Webhooks`.
4. Click `Add New Webhook to Workspace`.
5. Choose the channel where KyulAI updates should appear.
6. Copy the generated webhook URL.

Local setup:

```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
```

Send a one-off test:

```bash
python3 scripts/slack-bridge.py --send-test
```

Forward all future bus events:

```bash
python3 scripts/slack-bridge.py
```

Forward pending historical events once:

```bash
python3 scripts/slack-bridge.py --once --since beginning --reset-state
```

Dry-run without sending to Slack:

```bash
python3 scripts/slack-bridge.py --send-test --dry-run
python3 scripts/slack-bridge.py --once --since beginning --reset-state --dry-run
```

## Slack Inbound Commands

Slack inbound commands are implemented through the DD FastAPI server:

```text
POST /slack/commands
```

Use this request URL in Slack:

```text
https://laminate.luvelox.com/slack/commands
```

Recommended Slash Command:

```text
/kyulai
```

Supported commands:

- `/kyulai task <text>` creates an orchestrator task.
- `/kyulai msg <agent> <text>` creates an agent-bus message.
- `/kyulai status` returns recent task counts and public URLs.
- `/kyulai help` returns usage help.

Required environment variable before running the DD server:

```bash
export SLACK_SIGNING_SECRET="..."
```

Optional allowlist:

```bash
export SLACK_ALLOWED_USER_IDS="U12345678,U23456789"
```

Then restart the DD server:

```bash
/Users/danlee/KyulAI_codex/.venv/bin/uvicorn src.backend.dd_laminate_app:app --host 127.0.0.1 --port 8000
```

Notes:

- The endpoint verifies Slack's `X-Slack-Signature` and
  `X-Slack-Request-Timestamp`.
- `SLACK_ALLOW_UNSIGNED_COMMANDS=1` exists only for local tests and should not
  be used for public operation.
- Slash Commands must receive a response quickly. The endpoint only writes to
  `.agent-bus/` and returns an acknowledgement; actual coding work still needs
  a local runner or an active Codex session to read and act on the bus.

## Codex Work Notifications

Use this when Codex needs to notify the user on a phone or watch that an
approval prompt needs attention, a long task finished, or a failure happened.
This is separate from the agent-bus Slack bridge and can be called directly.

Supported channels:

- Telegram: `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`
- Slack: `SLACK_WEBHOOK_URL`

Recommended private environment file:

```bash
mkdir -p ~/.codex
cat > ~/.codex/notify.env <<'EOF'
export TELEGRAM_BOT_TOKEN="123456:..."
export TELEGRAM_CHAT_ID="123456789"
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
EOF
chmod 600 ~/.codex/notify.env
```

Load it in the current terminal:

```bash
source ~/.codex/notify.env
```

Check which channels are available:

```bash
python3 scripts/codex-notify.py --status
```

Send a test notification:

```bash
python3 scripts/codex-notify.py test --channel auto \
  --message "Codex notification test from KyulAI."
```

Notify that a Codex approval prompt needs attention:

```bash
python3 scripts/codex-notify.py approval --channel auto \
  --message "Codex needs command approval. Please check the Codex app."
```

Notify that work is complete:

```bash
python3 scripts/codex-notify.py complete --channel auto \
  --message "Task complete. Tests passed and the APK artifact was refreshed."
```

Dry-run without sending:

```bash
python3 scripts/codex-notify.py approval --dry-run \
  --message "Preview only."
```

Notes:

- Phone/watch delivery depends on Telegram or Slack app notification settings.
- The script does not store secrets in the repository.
- Codex app approval buttons still must be pressed inside Codex; this script is
  a phone/watch nudge so the user knows to return to the app.
