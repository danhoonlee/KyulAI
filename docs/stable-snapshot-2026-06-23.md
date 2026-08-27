# Stable Snapshot - 2026-06-23

This snapshot preserves the currently working DD Laminate, Simple Injection,
ImperialAX/ImperialAX app shell, and Windows serving handoff state.

## Included

- DD Laminate web/API changes, including `/ready`, current Laminate Forecast
  and u3 Forecast model registry defaults, XAI payload handling, curve/Pt
  consistency helpers, and v2 frontend files.
- Simple Injection web/API changes, including `/ready`, current sprue/filling
  model availability checks, and v2 frontend files.
- ImperialAX/ImperialAX unified app shell, login/admin/optimization frontend files, and
  Android/iOS app changes needed for the current app handoff.
- Windows serving scripts:
  - `scripts/windows/Setup-WindowsServing.ps1`
  - `scripts/windows/Start-All.ps1`
  - `scripts/windows/Start-DD.ps1`
  - `scripts/windows/Start-Injection.ps1`
  - `scripts/windows/Start-CloudflareTunnel.ps1`
  - `scripts/windows/Check-Health.ps1`
  - `scripts/windows/Install-LogonTasks.ps1`
- Windows bundle packager:
  - `scripts/package_windows_bundle.py`
- Current API-referenced model directories that are already part of the serving
  handoff, plus compact research/challenger artifacts that stay below normal
  GitHub file-size limits.
- Current tracked datasets under `data/datasets`, including the tracked
  Double-Double and Simple Injection data already present in Git.
- Documentation, reports, tests, and session memory needed to resume the work.

## Excluded From Git Snapshot

- Local runtime files: `.venv`, logs, `__pycache__`, `.pytest_cache`,
  `.mypy_cache`, `.ruff_cache`, `.agent-bus`, local SQLite auth data, and OS
  metadata such as `.DS_Store` or `desktop.ini`.
- Cloudflare credential JSON files and `.env.local`.
- Two research-only tabular challenger model files that exceed normal GitHub
  file-size limits and are not used by the production serving registry:
  - `models/dd_laminate_response_tabular_challengers_v1/extra_trees.joblib`
    - about 453 MB
  - `models/dd_laminate_response_tabular_challengers_v1/random_forest.joblib`
    - about 215 MB

## Data And Model Handoff Policy

- Git is used for the stable source snapshot and for model/data files that are
  already tracked or small enough to be practical.
- The portable Windows handoff zip is the safer path when a new Windows server
  must receive ignored local dataset folders too:

```bash
python3 scripts/package_windows_bundle.py --output ~/Desktop/KyulAI_windows_server_bundle.zip
```

- After extraction on Windows, verify runtime readiness with:

```powershell
.\scripts\windows\Setup-WindowsServing.ps1
.\scripts\windows\Start-All.ps1 -SkipCloudflare
.\scripts\windows\Check-Health.ps1 -Ready -LocalOnly
```
