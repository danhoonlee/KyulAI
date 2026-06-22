# Windows Server Migration Guide

This guide moves the current DD Laminate and Simple Injection web apps from the
Mac to a Windows server PC.

## What Runs On The Server

The public setup has three long-running processes. Port `8000` is host-routed:
`ai.luvelox.com` serves the C2ES App login/module workspace, while
`laminate.luvelox.com` serves the Laminate forecast UI.

| Process | Local URL | Public URL |
|---|---|---|
| C2ES App + DD Laminate | `http://127.0.0.1:8000` | `https://ai.luvelox.com`, `https://laminate.luvelox.com` |
| Simple Injection | `http://127.0.0.1:8010` | `https://injection.luvelox.com` |
| Cloudflare Tunnel | routes hostnames | Cloudflare edge |

No inbound firewall port needs to be opened if Cloudflare Tunnel is used.

Each app exposes two status endpoints:

- `/health`: process liveness only.
- `/ready`: verifies that the serving models and Python dependencies are
  available. Use this before showing the app to someone else.

## Recommended Transfer Method

### Option A: Git Clone

The current Git handoff includes code, curated datasets, trained models,
reports, Windows scripts, and app artifacts. On a fresh Windows PC:

```powershell
cd C:\
git clone https://github.com/danhoonlee/KyulAI.git KyulAI_codex
cd C:\KyulAI_codex
git checkout codex/dd-laminate-ui-api
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\Setup-WindowsServing.ps1
```

Then start local servers:

```powershell
.\scripts\windows\Start-All.ps1 -SkipCloudflare
```

This starts both DD Laminate and Simple Injection, then runs a local readiness
check.

Open:

- DD Laminate: `http://127.0.0.1:8000`
- Simple Injection: `http://127.0.0.1:8010`

For the condensed Git-based checklist, see
`docs/WINDOWS_GIT_QUICKSTART.md`.

### Option B: Portable Zip Bundle

Use the portable serving bundle. A plain Git clone may miss large ignored data
folders such as `data/datasets`.

On the Mac:

```bash
cd /Users/danlee/KyulAI_codex
python3 scripts/package_windows_bundle.py --output ~/Desktop/KyulAI_windows_server_bundle.zip
```

Move `KyulAI_windows_server_bundle.zip` to the Windows server and unzip it to:

```powershell
C:\KyulAI_codex
```

The bundle includes the runtime code, current models, DD curated data, Simple
Injection data needed by the UI, the Luvelox/C2ES shell UI, Windows scripts,
and docs. It intentionally does not include `.venv`, `.git`, local logs, or
secrets.

## Windows Prerequisites

Install:

- Python 3.11 x64
- Cloudflared
- Git is optional if using the zip bundle

If `winget` is available:

```powershell
winget install Python.Python.3.11
winget install Cloudflare.cloudflared
```

Close and reopen PowerShell after installing Python or cloudflared so `py` and
`cloudflared.exe` are on PATH.

## Python Environment

Open PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
cd C:\KyulAI_codex
.\scripts\windows\Setup-WindowsServing.ps1
```

If the `py -3.11` launcher does not work:

```powershell
.\scripts\windows\Setup-WindowsServing.ps1 -Python "python"
```

The setup script:

- creates `.venv`
- installs `requirements-serving.txt`
- installs the PyTorch CPU wheel
- verifies the main runtime imports
- prints a DD/Injection model readiness summary

## Local Secrets

Copy the example env file:

```powershell
cd C:\KyulAI_codex
Copy-Item .env.windows.example .env.local
notepad .env.local
```

For normal web prediction, `.env.local` can stay mostly empty.

For Slack slash commands, set:

```text
SLACK_SIGNING_SECRET=your_slack_signing_secret
```

Do not commit or send `.env.local`.

## Cloudflare Tunnel Credentials

The current named tunnel is:

```text
kclab-composite-ai
02b4b689-84ef-4459-91cd-48c81ea549ae
```

The primary DNS routes point to this tunnel:

- `laminate.luvelox.com`
- `injection.luvelox.com`

Legacy DNS routes should remain available during the migration:

- `dd.cafedecafe.co.kr`
- `injection.cafedecafe.co.kr`

On the Mac, the tunnel credential file is currently expected at:

```text
/Users/danlee/.cloudflared/02b4b689-84ef-4459-91cd-48c81ea549ae.json
```

Copy that JSON file securely to the Windows server, for example:

```text
C:\Users\<WINDOWS_USER>\.cloudflared\02b4b689-84ef-4459-91cd-48c81ea549ae.json
```

Treat this JSON file like a password. Do not put it in Git or a public email.

Then create the Windows tunnel config:

```powershell
cd C:\KyulAI_codex
Copy-Item infrastructure\cloudflare\kclab-composite-ai.windows.example.yml infrastructure\cloudflare\kclab-composite-ai.windows.yml
notepad infrastructure\cloudflare\kclab-composite-ai.windows.yml
```

Edit `credentials-file` so it points to the copied Windows JSON path.

It is okay for the Mac and Windows server to run connectors for the same named
tunnel at the same time during migration. After Windows is confirmed stable,
stop the Mac tunnel to avoid confusion.

## First Manual Start

Start local servers first, without Cloudflare:

```powershell
cd C:\KyulAI_codex
.\scripts\windows\Start-All.ps1 -SkipCloudflare
```

Then verify:

```powershell
.\scripts\windows\Check-Health.ps1 -Ready -LocalOnly
```

Expected output should show HTTP 200 for:

- DD local
- Injection local

After the local check passes and the Cloudflare config is ready, start all
processes:

```powershell
.\scripts\windows\Start-All.ps1
```

Then verify both local and public readiness:

```powershell
.\scripts\windows\Check-Health.ps1 -Ready
```

If you want to debug foreground logs, open three PowerShell windows and run:

```powershell
cd C:\KyulAI_codex
.\scripts\windows\Start-DD.ps1
```

```powershell
cd C:\KyulAI_codex
.\scripts\windows\Start-Injection.ps1
```

```powershell
cd C:\KyulAI_codex
.\scripts\windows\Start-CloudflareTunnel.ps1
```

## Keep It Running

For a first pass, install logon tasks:

```powershell
cd C:\KyulAI_codex
.\scripts\windows\Install-LogonTasks.ps1
```

Start them immediately:

```powershell
Start-ScheduledTask -TaskName KyulAI-DD
Start-ScheduledTask -TaskName KyulAI-Injection
Start-ScheduledTask -TaskName KyulAI-CloudflareTunnel
```

This is good if the Windows server automatically logs in after reboot. For a
true unattended server that should run before login, use Windows Services or
NSSM later. The same three scripts can be wrapped as services.

## Updating Later

When code/models/data change on the Mac:

1. Create a fresh zip with `scripts/package_windows_bundle.py`.
2. Stop the Windows tasks/processes.
3. Replace the files in `C:\KyulAI_codex`.
4. Keep `.env.local` and the Cloudflare credential JSON.
5. Re-run `Setup-WindowsServing.ps1` only if dependencies changed.
6. Start and check health.

## Common Problems

### `Start-All.ps1` says Cloudflare config is missing

For local testing, run:

```powershell
.\scripts\windows\Start-All.ps1 -SkipCloudflare
```

For public URLs, create:

```text
C:\KyulAI_codex\infrastructure\cloudflare\kclab-composite-ai.windows.yml
```

from the `.example.yml` file and set the correct `credentials-file` path.

### Public URLs show Cloudflare 530 / 1033

The local apps may be fine, but the tunnel is down.

Run:

```powershell
.\scripts\windows\Start-CloudflareTunnel.ps1
```

Then:

```powershell
.\scripts\windows\Check-Health.ps1 -PublicOnly
```

### Public DD is 502

The tunnel is alive, but DD local server is down.

Run:

```powershell
.\scripts\windows\Start-DD.ps1
```

### Public Injection is 502

The tunnel is alive, but Injection local server is down.

Run:

```powershell
.\scripts\windows\Start-Injection.ps1
```

### Deep-learning model options show missing

PyTorch is probably not installed in `.venv`.

Run:

```powershell
.\.venv\Scripts\python.exe -m pip install torch==2.2.0 --index-url https://download.pytorch.org/whl/cpu
```

Then check:

```powershell
.\scripts\windows\Check-Health.ps1 -Ready -LocalOnly
```

If `/ready` reports a missing model file, the zip or Git checkout is missing
that `models\...` folder.

### Slack `/kyulai` returns server configuration error

Set `SLACK_SIGNING_SECRET` in `.env.local`, then restart DD.

## Current Best Quick Checklist

On Mac:

```bash
cd /Users/danlee/KyulAI_codex
python3 scripts/package_windows_bundle.py --output ~/Desktop/KyulAI_windows_server_bundle.zip
```

On Windows:

```powershell
Expand-Archive .\KyulAI_windows_server_bundle.zip C:\KyulAI_codex
cd C:\KyulAI_codex
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\Setup-WindowsServing.ps1
Copy-Item .env.windows.example .env.local
.\scripts\windows\Start-All.ps1 -SkipCloudflare
.\scripts\windows\Check-Health.ps1 -Ready -LocalOnly
Copy-Item infrastructure\cloudflare\kclab-composite-ai.windows.example.yml infrastructure\cloudflare\kclab-composite-ai.windows.yml
notepad infrastructure\cloudflare\kclab-composite-ai.windows.yml
.\scripts\windows\Start-All.ps1
.\scripts\windows\Check-Health.ps1 -Ready
```
