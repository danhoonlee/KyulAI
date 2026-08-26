# ImperialAX WSL Serving Operations

## Current architecture

ImperialAX production traffic is served from the home Windows PC through Ubuntu on WSL2.

- WSL host: `user@100.65.153.56` through Tailscale
- WSL repository: `/home/user/projects/KyulAI`
- Laminate API: `127.0.0.1:8000`
- Injection API: `127.0.0.1:8010`
- Cloudflare Tunnel: `imperialax-wsl-serving`
- Tunnel ID: `e8928d27-7518-4ba9-ac36-108ca3a78718`
- Tunnel config: `/home/user/projects/KyulAI/infrastructure/cloudflare/imperialax-wsl.yml`

The previous Mac tunnel launch agent is now disabled after the remaining CafeDeCafe routes were
migrated to their own WSL tunnel. Its Cloudflare tunnel object is retained only for rollback.

## Security defaults

The public services bind only to `127.0.0.1`; Cloudflare Tunnel is the only
network path to the origin. `IMPERIALAX_ENV=production` is set by systemd, so
`IMPERIALAX_DISABLE_AUTH_FOR_LOCAL_DEV=1` causes startup to fail instead of
silently exposing prediction APIs.

- Laminate and Injection prediction APIs require an entitled session.
- Web sessions use `HttpOnly`, `Secure`, `SameSite=Lax` cookies scoped to
  `.imperialax.com`; native applications use bearer headers.
- Native-to-web transitions use 60-second, single-use launch codes.
- Demo sessions expire after 4 hours and prediction/login/upload limits return
  HTTP `429` with `Retry-After`.
- Keep Uvicorn at one worker with the built-in limiter. Move counters to Redis
  before scaling to multiple workers or hosts.

## Public routes

| URL | Origin |
| --- | --- |
| `https://imperialax.com` | Laminate API |
| `https://www.imperialax.com` | Laminate API |
| `https://ai.imperialax.com` | Laminate API |
| `https://app.imperialax.com` | Laminate API |
| `https://laminate.imperialax.com` | Laminate API |
| `https://dd.imperialax.com` | Laminate API |
| `https://injection.imperialax.com` | Injection API |

## Service control

Connect from the Mac with the project runner:

```bash
cd /Users/danlee/KyulAI_codex
scripts/remote/Run-WSLGPU.sh 'systemctl --user status imperialax-laminate.service imperialax-injection.service imperialax-cloudflared.service'
```

Start, restart, or stop all services inside WSL:

```bash
systemctl --user start imperialax-laminate.service imperialax-injection.service imperialax-cloudflared.service
systemctl --user restart imperialax-laminate.service imperialax-injection.service imperialax-cloudflared.service
systemctl --user stop imperialax-cloudflared.service imperialax-injection.service imperialax-laminate.service
```

The services are enabled in the WSL user systemd instance. Windows also runs
`Start-ImperialAX-WSL-Serving.cmd` from the current user's Startup folder after login so WSL starts automatically.

## Health and readiness

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/ready
curl -fsS http://127.0.0.1:8010/health
curl -fsS http://127.0.0.1:8010/ready

curl -fsS https://laminate.imperialax.com/health
curl -fsS https://laminate.imperialax.com/ready
curl -fsS https://injection.imperialax.com/health
curl -fsS https://injection.imperialax.com/ready
```

`/health` proves that the API process responds. `/ready` additionally verifies that the required model artifacts loaded successfully.

## Logs

```bash
journalctl --user -u imperialax-laminate.service -n 100 --no-pager
journalctl --user -u imperialax-injection.service -n 100 --no-pager
journalctl --user -u imperialax-cloudflared.service -n 100 --no-pager

tail -f /home/user/projects/KyulAI/logs/imperialax-laminate.err.log
tail -f /home/user/projects/KyulAI/logs/imperialax-injection.err.log
tail -f /home/user/projects/KyulAI/logs/imperialax-cloudflared.err.log
```

## Windows startup

Repository scripts:

- `scripts/windows/Start-ImperialAX-WSL-Serving.cmd`
- `scripts/windows/Check-ImperialAX-WSL-Serving.cmd`

Installed startup location:

```text
C:\Users\user\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\ImperialAX-WSL-Serving.cmd
```

The same startup script also starts the CafeDeCafe Tunnel, Nangman RAG API, and Nangman refresh
timer. The Windows PC must remain powered on, connected to the internet, and signed in. Windows
sleep or shutdown stops the public services until the PC and WSL start again.

## Deployment update

Sync only reviewed files and model artifacts to `/home/user/projects/KyulAI`, then restart the affected service. Keep `.env.local`, the authentication database, Cloudflare credentials, and admin tokens out of Git and transfer them through the secured SSH path.

Before replacing source files, create a remote backup:

```bash
cd /home/user/projects/KyulAI
mkdir -p .remote-backups
tar -czf ".remote-backups/pre_update_$(date +%Y%m%d_%H%M%S).tgz" src scripts infrastructure pyproject.toml
```

After deployment, validate both `/ready` endpoints and run one real Laminate and Injection prediction before considering the update complete.

## DNS rollback

The former Mac tunnel ID is `02b4b689-84ef-4459-91cd-48c81ea549ae`. If the WSL host cannot be recovered and an urgent rollback is needed, run the following from a machine authenticated to the same Cloudflare account:

```bash
for host in imperialax.com www.imperialax.com ai.imperialax.com app.imperialax.com laminate.imperialax.com dd.imperialax.com injection.imperialax.com; do
  cloudflared tunnel route dns --overwrite-dns 02b4b689-84ef-4459-91cd-48c81ea549ae "$host"
done
```

Confirm the Mac APIs and old tunnel are healthy before rollback. To return traffic to WSL, repeat the command with tunnel ID `e8928d27-7518-4ba9-ac36-108ca3a78718`.
