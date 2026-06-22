# Unified C2ES App Direction

C2ES should move from one app per model to one account-based app with
server-controlled modules.

## Target Product Shape

- One app name: C2ES
- One module dashboard: Laminate, Injection, and future CAE-AI models
- One login/account surface
- Shared history, sharing, reports, language settings, and API status handling
- Module access controlled by server-side entitlements

## Initial Contract

The unified app should call:

- `GET /api/v1/modules`
- `GET /api/v1/modules/me`

`/modules` returns the full product catalog. `/modules/me` returns the modules
visible to the current user and whether each one is `granted` or `locked`.

For the MVP, Laminate and Injection are granted by default. Future modules can
be unlocked in development with:

```text
X-Luvelox-Entitlements: module.optimization
```

or:

```text
/api/v1/modules/me?entitlements=module.optimization
```

## Recommended Migration

1. Keep the current Laminate and Injection apps stable.
2. Use the new module API as the shared source of truth.
3. Build a C2ES shell app with a module dashboard.
4. Move Laminate into the shell as the first native module.
5. Move Injection into the shell as the second native module.
6. Add login and account/session tokens.
7. Replace demo entitlements with database-backed license grants.
8. Add a web admin page for account and module access management.

## Local Preview

Run the unified shell:

```bash
uvicorn src.backend.luvelox_app:app --reload --port 8000
```

Then open:

```text
http://127.0.0.1:8000
```

The web C2ES App entry now lives at:

- `https://ai.luvelox.com`

Standalone module domains continue to run in parallel and are opened from the
AI workspace:

- `https://laminate.luvelox.com`
- `https://injection.luvelox.com`

## Native Shell MVP

The first native unified shell exists in:

- `ios/LuveloxMVP`
- `android/LuveloxMVP`

Both apps currently:

- Show a C2ES module dashboard.
- Fetch `GET /api/v1/modules/me`.
- Fall back to built-in Laminate and Injection cards if the catalog request
  fails.
- Open Laminate as a native module inside the C2ES shell.
- Open Injection as a native module inside the C2ES shell.

The catalog request currently points at:

```text
https://laminate.luvelox.com/api/v1/modules/me
```

Later, when `api.luvelox.com` is routed, this should move to:

```text
https://api.luvelox.com/api/v1/modules/me
```

### iOS

```bash
cd ios/LuveloxMVP
swift test
swift build
```

Open `ios/LuveloxMVP/Package.swift` in Xcode and run
`LuveloxPreviewApp` to preview the shell.

### Android

```bash
cd android/LuveloxMVP
JAVA_HOME=/opt/homebrew/opt/openjdk@17 gradle :app:assembleDebug
```

Debug APK:

```text
artifacts/android/Luvelox-debug.apk
```

## Native Modules

The first native module integrations are Laminate and Injection.

iOS:

- `ios/LuveloxMVP` depends on the existing `ios/DDLaminateMVP`
  `KyulAIDDLaminateCore` product.
- `ios/LuveloxMVP` also depends on the existing `ios/InjectionMVP`
  `KyulAIInjectionCore` product.
- `LaminateForecastView` runs native case/theta/model selection and calls
  `POST /api/v1/dd-laminate/predict/response`.
- `InjectionForecastView` runs native geometry/process/model selection and calls
  `POST /api/v1/simple-injection/predict/sprue-pressure`.
- The C2ES Laminate and Injection cards navigate to native views.

Android:

- `android/LuveloxMVP` includes `LaminateActivity`.
- `android/LuveloxMVP` includes `InjectionActivity`.
- The C2ES Laminate and Injection cards open native Activities instead of the
  browser.
- The Activity calls the same Laminate models and response prediction API.
- The Injection Activity calls the same Simple Injection models, DOE catalog,
  and sprue/filling prediction API.

The next migration step is to bring richer charts, recent history, and sharing
from the standalone module apps into the unified C2ES native modules.
