# Laminate Forecast existing-app EXE packaging note

This note is for packaging the Laminate app that already exists in this
repository. It is different from the greenfield Codex handoff package made for
rebuilding the app from scratch.

## Existing app entry points

- Backend app: `src/backend/dd_laminate_app.py`
- Laminate API router: `src/backend/api/v1/dd_laminate.py`
- Module/auth API router: `src/backend/api/v1/modules.py`
- Auth store: `src/backend/services/luvelox_auth_store.py`
- Frontend UI: `src/frontend/dd-laminate/index-v2.html`
- Korean UI: `src/frontend/dd-laminate/index-v2.ko.html`
- Main frontend logic: `src/frontend/dd-laminate/app-v2.js`
- License gate: `src/frontend/dd-laminate/auth-gate.js`

## License/login behavior

The Laminate page now has a license login gate. It uses the existing ImperialAX
auth API:

- Login endpoint: `/api/v1/modules/auth/login`
- Session check endpoint: `/api/v1/modules/me`
- Required entitlement: `module.laminate`

The frontend stores the session in:

```text
localStorage["luvelox.auth.session.v1"]
```

The frontend also attaches the bearer token to Laminate API requests.

For real packaged EXE builds, the backend should be started with:

```text
LAMINATE_REQUIRE_AUTH=1
LUVELOX_DISABLE_DEMO_LOGIN=1
```

When `LAMINATE_REQUIRE_AUTH=1`, `/api/v1/dd-laminate/*` requires a valid bearer
token with `module.laminate` access.

## Creating a licensed user

On Windows, from the project root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\exe\Create-LaminateUser.ps1 `
  -Email "researcher@example.com" `
  -Password "ChangeThisPassword123!" `
  -Name "Researcher"
```

This creates or updates the local SQLite auth database at:

```text
data\luvelox_auth.sqlite3
```

The EXE bundle copies this database with the app, so the issued ID/password can
be used inside the portable app.

## Building the EXE bundle

The EXE build must be run on Windows because PyInstaller creates executables for
the current operating system.

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\exe\Build-LaminateExe.ps1
```

Output:

```text
dist\windows\LaminateForecast-existing-win-x64-portable
```

Run:

```powershell
.\dist\windows\LaminateForecast-existing-win-x64-portable\LaminateForecast.exe
```

## Bundle structure

```text
LaminateForecast-existing-win-x64-portable\
  LaminateForecast.exe
  backend\
    laminate_backend.exe
  src\
    backend\
    frontend\dd-laminate\
    frontend\luvelox\
  data\
  models\
  README.txt
```

## Security caveat

This is local account/entitlement gating, suitable for controlled demos and
limited internal distribution. For stronger commercial licensing, add one of
these later:

- server-side license activation against an ImperialAX license API
- signed offline license files bound to machine ID
- time-limited trial license and periodic revalidation
- installer-level code signing and tamper checks
