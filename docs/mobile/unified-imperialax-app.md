# Unified ImperialAX App Direction

ImperialAX should move from one app per model to one account-based app with
server-controlled modules.

## Target Product Shape

- One app name: ImperialAX
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
X-ImperialAX-Entitlements: module.optimization
```

or:

```text
/api/v1/modules/me?entitlements=module.optimization
```

## Recommended Migration

1. Keep the current Laminate and Injection apps stable.
2. Use the new module API as the shared source of truth.
3. Build an ImperialAX shell app with a module dashboard.
4. Move Laminate into the shell as the first native module.
5. Move Injection into the shell as the second native module.
6. Add login and account/session tokens.
7. Replace demo entitlements with database-backed license grants.
8. Add a web admin page for account and module access management.

## Local Preview

Run the unified shell:

```bash
uvicorn src.backend.imperialax_app:app --reload --port 8000
```

Then open:

```text
http://127.0.0.1:8000
```

The web ImperialAX App entry now lives at:

- `https://ai.imperialax.com`

Standalone module domains continue to run in parallel and are opened from the
AI workspace:

- `https://laminate.imperialax.com`
- `https://injection.imperialax.com`

## Native Shell MVP

The first native unified shell exists in:

- `ios/ImperialAXMVP`
- `android/ImperialAXMVP`

Both apps currently:

- Show an ImperialAX module dashboard.
- Fetch `GET /api/v1/modules/me`.
- Fall back to built-in Laminate and Injection cards if the catalog request
  fails.
- Open Laminate as a native module inside the ImperialAX shell.
- Open Injection as a native module inside the ImperialAX shell.

The catalog request currently points at:

```text
https://laminate.imperialax.com/api/v1/modules/me
```

Later, when `api.imperialax.com` is routed, this should move to:

```text
https://api.imperialax.com/api/v1/modules/me
```

### iOS

```bash
cd ios/ImperialAXMVP
swift test
swift build
```

Open `ios/ImperialAXMVP/Package.swift` in Xcode and run
`ImperialAXPreviewApp` to preview the shell.

### Android

```bash
cd android/ImperialAXMVP
JAVA_HOME=/opt/homebrew/opt/openjdk@17 gradle :app:assembleDebug
```

Debug APK:

```text
artifacts/android/ImperialAX-debug.apk
```

## Native Modules

The first native module integrations are Laminate and Injection.

iOS:

- `ios/ImperialAXMVP` depends on the existing `ios/DDLaminateMVP`
  `KyulAIDDLaminateCore` product.
- `ios/ImperialAXMVP` also depends on the existing `ios/InjectionMVP`
  `KyulAIInjectionCore` product.
- `LaminateForecastView` runs native case/theta/model selection and calls
  `POST /api/v1/dd-laminate/predict/response`.
- `InjectionForecastView` runs native geometry/process/model selection and calls
  `POST /api/v1/simple-injection/predict/sprue-pressure`.
- The ImperialAX Laminate and Injection cards navigate to native views.

Android:

- `android/ImperialAXMVP` includes `LaminateActivity`.
- `android/ImperialAXMVP` includes `InjectionActivity`.
- The ImperialAX Laminate and Injection cards open native Activities instead of the
  browser.
- The Activity calls the same Laminate models and response prediction API.
- The Injection Activity calls the same Simple Injection models, DOE catalog,
  and sprue/filling prediction API.

The next migration step is to bring richer charts, recent history, and sharing
from the standalone module apps into the unified ImperialAX native modules.
