# Laminate Forecast existing-app Windows EXE build

This build kit packages the current completed Laminate Forecast app, not the
greenfield rebuild package.

## What it creates

- `LaminateForecast.exe`: double-click desktop launcher
- `backend/laminate_backend.exe`: local FastAPI backend
- `src/frontend/dd-laminate`: current web UI
- `src/backend`: current prediction/RAG/auth API code
- `models` and `data`: current model and dataset artifacts

## Security mode

The launcher starts the backend with:

- `LAMINATE_REQUIRE_AUTH=1`
- `IMPERIALAX_DISABLE_DEMO_LOGIN=1`

That means the Laminate prediction API requires a signed-in account with
`module.laminate` entitlement. The frontend also displays a license login gate
before use.

## Build on Windows

From the project root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\exe\Build-LaminateExe.ps1
```

Before sharing the bundle, create at least one licensed user:

```powershell
.\scripts\windows\exe\Create-LaminateUser.ps1 `
  -Email "researcher@example.com" `
  -Password "ChangeThisPassword123!" `
  -Name "Researcher"
```

The generated `data\imperialax_auth.sqlite3` file is copied into the portable
bundle by `Build-LaminateExe.ps1`.

The portable bundle is created at:

```text
dist\windows\LaminateForecast-existing-win-x64-portable
```

Run:

```powershell
.\dist\windows\LaminateForecast-existing-win-x64-portable\LaminateForecast.exe
```

## Notes

This script is prepared on macOS but should be run on Windows because PyInstaller
must build the `.exe` on the target OS.
