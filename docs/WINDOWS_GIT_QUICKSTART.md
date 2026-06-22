# Windows Git Quickstart

This is the shortest path for running the current DD Laminate and Simple
Injection apps on a Windows PC after cloning from GitHub.

## 1. Install Required Programs

Install these first:

- Git for Windows
- Python 3.11 x64
- Cloudflared, only if this PC will serve the public domains

With PowerShell and `winget`:

```powershell
winget install Git.Git
winget install Python.Python.3.11
winget install Cloudflare.cloudflared
```

Close and reopen PowerShell after installing.

## 2. Clone The Project

```powershell
cd C:\
git clone https://github.com/danhoonlee/KyulAI.git KyulAI_codex
cd C:\KyulAI_codex
git checkout codex/dd-laminate-ui-api
```

This branch includes the current code, curated datasets, trained models,
reports, Windows scripts, and app artifacts. It does not include local secrets.

## 3. Create The Python Environment

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\Setup-WindowsServing.ps1
```

If `py -3.11` is not found:

```powershell
.\scripts\windows\Setup-WindowsServing.ps1 -Python "python"
```

The setup script creates `.venv`, installs serving dependencies, installs the
CPU PyTorch wheel, checks the main imports, and prints a model readiness
summary.

## 4. Create Local Environment File

```powershell
Copy-Item .env.windows.example .env.local
notepad .env.local
```

For normal DD/Injection prediction, you can leave `.env.local` mostly empty.
Only fill Slack values if Slack slash commands are needed.

Never commit `.env.local`.

## 5. Run Locally First

Start both local servers first, without Cloudflare:

```powershell
cd C:\KyulAI_codex
.\scripts\windows\Start-All.ps1 -SkipCloudflare
```

Then open:

- DD Laminate: `http://127.0.0.1:8000`
- Simple Injection: `http://127.0.0.1:8010`

Readiness check:

```powershell
.\scripts\windows\Check-Health.ps1 -Ready -LocalOnly
```

If you prefer foreground logs, run these in two separate PowerShell windows:

```powershell
.\scripts\windows\Start-DD.ps1
```

```powershell
.\scripts\windows\Start-Injection.ps1
```

## 6. Public Cloudflare Setup

Only do this on the Windows server PC that should keep the public URLs alive.

Copy the Cloudflare tunnel credential JSON securely to:

```text
C:\Users\<WINDOWS_USER>\.cloudflared\
```

Then create the Windows tunnel config:

```powershell
Copy-Item infrastructure\cloudflare\kclab-composite-ai.windows.example.yml infrastructure\cloudflare\kclab-composite-ai.windows.yml
notepad infrastructure\cloudflare\kclab-composite-ai.windows.yml
```

Edit `credentials-file` to point to the copied JSON file. Do not put the JSON
credential file in Git.

Start all server processes:

```powershell
.\scripts\windows\Start-All.ps1
```

Then verify public and local readiness:

```powershell
.\scripts\windows\Check-Health.ps1 -Ready
```

## 7. Keep It Running After Reboot

```powershell
.\scripts\windows\Install-LogonTasks.ps1
Start-ScheduledTask -TaskName KyulAI-DD
Start-ScheduledTask -TaskName KyulAI-Injection
Start-ScheduledTask -TaskName KyulAI-CloudflareTunnel
```

## 8. Updating Later

```powershell
cd C:\KyulAI_codex
git pull
.\scripts\windows\Setup-WindowsServing.ps1
.\scripts\windows\Start-All.ps1 -SkipCloudflare
.\scripts\windows\Check-Health.ps1 -Ready -LocalOnly
```

Re-run setup after dependency changes. For normal code/model/data updates,
`git pull` and restarting the two app servers is usually enough.
