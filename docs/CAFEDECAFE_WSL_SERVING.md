# CafeDeCafe WSL Serving Operations

## Current architecture

CafeDeCafe production traffic is served from the home Windows PC through Ubuntu on WSL2.

- WSL host: `user@100.65.153.56` through Tailscale
- Main repository: `/home/user/projects/KyulAI`
- Nangman repository: `/home/user/projects/nangman-rag`
- Wedding and Laminate origin: `127.0.0.1:8000`
- Injection origin: `127.0.0.1:8010`
- Nangman RAG origin: `127.0.0.1:8020`
- Cloudflare Tunnel: `cafedecafe-wsl-serving`
- Tunnel ID: `68025491-2fa9-48a3-bc61-9caf6bd8e6d5`
- Tunnel config: `/home/user/projects/KyulAI/infrastructure/cloudflare/cafedecafe-wsl.yml`

The former Mac Cloudflare launch agent is disabled. Its tunnel object and local origins remain
available as an emergency rollback path, but production DNS points to the WSL tunnel.

## Public routes

| URL | WSL origin |
| --- | --- |
| `https://cafedecafe.co.kr` | Wedding routing on port 8000 |
| `https://www.cafedecafe.co.kr` | Main routing on port 8000 |
| `https://ds-wedding.cafedecafe.co.kr` | Wedding UI on port 8000 |
| `https://laminate.cafedecafe.co.kr` | Laminate UI and API on port 8000 |
| `https://dd.cafedecafe.co.kr` | Laminate UI and API on port 8000 |
| `https://injection.cafedecafe.co.kr` | Injection UI and API on port 8010 |
| `https://nangman.cafedecafe.co.kr` | Authenticated Nangman RAG on port 8020 |

## WSL services

```bash
systemctl --user status imperialax-laminate.service
systemctl --user status imperialax-injection.service
systemctl --user status cafedecafe-nangman.service
systemctl --user status cafedecafe-nangman-sync.timer
systemctl --user status cafedecafe-cloudflared.service
```

Restart the CafeDeCafe-specific services:

```bash
systemctl --user restart cafedecafe-nangman.service cafedecafe-cloudflared.service
systemctl --user restart cafedecafe-nangman-sync.timer
```

The Windows Startup script also starts these services after the user signs in:

```text
C:\Users\user\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\ImperialAX-WSL-Serving.cmd
```

## Nangman data refresh

`cafedecafe-nangman-sync.timer` runs the following incremental DCInside collection every 15 minutes:

```bash
/home/user/projects/nangman-rag/.venv/bin/romance-rag dc-sync \
  --pages 3 --max-posts 100 --delay 0.7
```

Check the next run and the most recent result:

```bash
systemctl --user list-timers --all cafedecafe-nangman-sync.timer
systemctl --user status cafedecafe-nangman-sync.service
tail -n 100 /home/user/projects/nangman-rag/logs/dc-sync.out.log
tail -n 100 /home/user/projects/nangman-rag/logs/dc-sync.err.log
```

The production SQLite database is `/home/user/projects/nangman-rag/data/romance.db`. Preserve it
when updating source code. The `.env` file contains private API and access credentials and must not
be committed to Git.

## Wedding persistent data

The wedding UI is served from the directory named by `WEDDING_FRONTEND_DIR`, which is set in the
systemd drop-in `~/.config/systemd/user/imperialax-laminate.service.d/wedding-frontend.conf` to
`/home/user/projects/donghoon-seyeon-wedding` (a separate git repo, deployed via SSH file sync).
The in-tree `src/frontend/wedding` is only the code's fallback default and now holds a **stale
2025-07-22 copy** (see its `DO-NOT-USE.md`); do not edit or deploy it, and do not remove the
drop-in or the site silently rolls back to that old copy. Guestbook and attendance records are
runtime data and are not part of the frontend deployment:

```text
/home/user/projects/KyulAI/runtime/wedding/rsvp-submissions.jsonl
/home/user/projects/KyulAI/runtime/wedding/admin-token.txt
```

Preserve both files when syncing source or rebuilding the WSL checkout. The JSONL file contains
guestbook, RSVP, and bus records together. The token file preserves access to the existing wedding
admin page. Keep both files private and never commit them to Git.

Before replacing wedding runtime data, stop `imperialax-laminate.service`, back up the directory,
install the files with owner-only permissions, and restart the service. The pre-restore WSL backup
created during the July 22 migration is stored under `.remote-backups` as
`wedding-runtime-before-restore-20260722-212722.tgz`.

The invitation fonts are self-hosted under `assets/fonts` in the deployed repo
(`donghoon-seyeon-wedding`). Do not reintroduce a runtime dependency on Google Fonts: Samsung
Internet may otherwise substitute an unreadable generic cursive font when the external stylesheet
or font request is unavailable.

The scripted couple name on the first cover is intentionally rendered from
`assets/donghoon-seyeon-signature.png` in the deployed repo, so it remains visually identical even
when a mobile browser blocks every web-font request.

## Automated persistent-state backup

`imperialax-serving-backup.timer` creates a consistent backup every day at approximately 03:15
KST, with up to ten minutes of randomized delay. Backups are written outside the WSL virtual disk:

```text
C:\Users\user\ImperialAX-Backups
```

The most recent 14 archives are retained. Each archive includes:

- Wedding RSVP, guestbook, and administrator state.
- ImperialAX authentication SQLite databases and administrator token.
- Laminate and Nangman private environment configuration.
- A SQLite online snapshot of the Nangman knowledge database.
- Cloudflare Tunnel credentials and installed WSL user service definitions.

The backup script validates wedding JSONL, runs SQLite integrity checks, verifies the generated
archive, and writes a SHA-256 sidecar file. Run and inspect it manually with:

```bash
systemctl --user start imperialax-serving-backup.service
systemctl --user status imperialax-serving-backup.service
systemctl --user list-timers --all imperialax-serving-backup.timer
ls -lh /mnt/c/Users/user/ImperialAX-Backups
```

The Windows backup directory inherits an ACL limited to the current Windows user, Administrators,
and SYSTEM. Do not move the archives into a shared folder because they contain private credentials.

## Health checks

```bash
curl -fsS http://127.0.0.1:8000/ready
curl -fsS http://127.0.0.1:8010/ready
curl -fsS http://127.0.0.1:8020/health

curl -fsS https://laminate.cafedecafe.co.kr/ready
curl -fsS https://injection.cafedecafe.co.kr/ready
curl -fsS https://nangman.cafedecafe.co.kr/health
curl -fsS https://ds-wedding.cafedecafe.co.kr/api/guestbook
```

The Nangman home and question endpoints use HTTP Basic authentication. A `401` response without
credentials is expected; an authenticated request must return `200`.

## Logs

```bash
journalctl --user -u cafedecafe-nangman.service -n 100 --no-pager
journalctl --user -u cafedecafe-nangman-sync.service -n 100 --no-pager
journalctl --user -u cafedecafe-cloudflared.service -n 100 --no-pager

tail -f /home/user/projects/nangman-rag/logs/server.err.log
tail -f /home/user/projects/KyulAI/logs/cafedecafe-cloudflared.err.log
```

## Emergency rollback to the Mac

The former tunnel ID is `02b4b689-84ef-4459-91cd-48c81ea549ae`. Confirm the Mac origins on ports
8000, 8010, and 8020 before changing DNS. Use the CafeDeCafe Cloudflare origin certificate, not the
ImperialAX certificate.

The former Mac API and Nangman launch agents were disabled after WSL verification. Re-enable and
start them before restoring the Mac Tunnel:

```bash
uid="$(id -u)"
launchctl enable "gui/${uid}/com.kyulai.dd-laminate-api"
launchctl enable "gui/${uid}/com.kyulai.simple-injection-api"
launchctl enable "gui/${uid}/com.cafedecafe.nangman-rag"
launchctl bootstrap "gui/${uid}" \
  /Users/danlee/Library/LaunchAgents/com.kyulai.dd-laminate-api.plist
launchctl bootstrap "gui/${uid}" \
  /Users/danlee/Library/LaunchAgents/com.kyulai.simple-injection-api.plist
launchctl bootstrap "gui/${uid}" \
  /Users/danlee/Library/LaunchAgents/com.cafedecafe.nangman-rag.plist
```

```bash
launchctl enable gui/$(id -u)/com.kyulai.cloudflare.kclab-composite-ai
launchctl bootstrap gui/$(id -u) \
  /Users/danlee/Library/LaunchAgents/com.kyulai.cloudflare.kclab-composite-ai.plist

for host in cafedecafe.co.kr www.cafedecafe.co.kr ds-wedding.cafedecafe.co.kr \
  laminate.cafedecafe.co.kr dd.cafedecafe.co.kr injection.cafedecafe.co.kr \
  nangman.cafedecafe.co.kr; do
  cloudflared --origincert /Users/danlee/.cloudflared/cert.cafedecafe-20260611.pem \
    tunnel route dns --overwrite-dns 02b4b689-84ef-4459-91cd-48c81ea549ae "$host"
done
```

After recovery, return the records to WSL by repeating the route command with tunnel ID
`68025491-2fa9-48a3-bc61-9caf6bd8e6d5`.

## Windows boot behavior

WSL user lingering is enabled for `user`, so the systemd user services survive the end of an SSH or
interactive shell session. The Windows Startup-folder script also starts every serving service and
both timers after login.

Starting WSL before interactive Windows login additionally requires one elevated Task Scheduler
registration. The installer is prepared on the Windows desktop:

```text
C:\Users\user\Desktop\Install-ImperialAX-WSL-BootTask.cmd
```

Double-click it and approve the UAC prompt once. Verify the installed task from an elevated
PowerShell window with:

```powershell
Get-ScheduledTask -TaskName "ImperialAX WSL Serving"
Get-ScheduledTaskInfo -TaskName "ImperialAX WSL Serving"
```

## Wedding root URL asset rule

The invitation is served both under `/wedding/` and directly at `https://cafedecafe.co.kr`.
Wedding pages must therefore reference shared assets with absolute `/wedding/assets/...` paths.
Do not use `./assets/...`; at the root URL it resolves to the unmounted `/assets/...` path and
causes fonts, images, icons, or calendar downloads to return 404.

The original wedding typography uses Google Fonts first and the static files under
`/wedding/assets/fonts/` as an offline fallback. Keep Cormorant Garamond split into static 400,
500, and 600 WOFF2 faces; the variable WOFF fallback did not render consistently in Samsung
Internet. Wedding pages are intentionally light-only and must keep both the
`<meta name="color-scheme" content="only light">` declaration and `color-scheme: only light` on
the root element so Samsung Internet does not apply automatic dark-theme transformations.
