# KyulAI Laminate iPhone SwiftUI MVP

This MVP is a thin SwiftUI client for the existing KyulAI Laminate FastAPI contract. It does
not embed Python, joblib, PyTorch, or ML model artifacts in the iPhone app. All predictions are
performed by the FastAPI server.

## Source layout

```text
ios/DDLaminateMVP/
  Package.swift
  Sources/KyulAIDDLaminateCore/      # Codable DTOs, API client, settings, view model, fixture loader
  Sources/KyulAIDDLaminateApp/       # SwiftUI app shell, settings/prediction/result screens, curve chart
  Tests/KyulAIDDLaminateCoreTests/   # Codable, base URL, fixture, and view model tests

ios/DDLaminateMVPApp/
  DDLaminateMVPHost.xcodeproj        # iOS host app for simulator/device launch
  DDLaminateMVPHost/Info.plist       # bundle id and local HTTP test settings
```

Open `ios/DDLaminateMVPApp/DDLaminateMVPHost.xcodeproj` when you want to run the app in an
iPhone simulator or on a physical device. Opening `ios/DDLaminateMVP/Package.swift` is useful for
package editing and tests, but the package executable does not provide the normal iOS app bundle
metadata needed by the simulator runtime.

The package includes the backend fixture at:

```text
ios/DDLaminateMVP/Sources/KyulAIDDLaminateCore/Resources/predict_response_case2.json
```

It mirrors:

```text
tests/fixtures/dd_laminate/predict_response_case2.json
```

## Run the FastAPI backend

From the repository root:

```bash
uvicorn src.backend.dd_laminate_app:app --host 0.0.0.0 --port 8000
```

Smoke-check the API from the Mac first:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/dd-laminate/models
```

## Real iPhone base URL setup

Do **not** enter `localhost` in the app on a physical iPhone. `localhost` means the phone itself,
not your Mac.

Use one of these base URLs in the app's API field:

1. Same Wi-Fi LAN IP for quick local testing:
   ```text
   http://<your-mac-lan-ip>:8000
   ```
2. HTTPS tunnel for demo/TestFlight-like testing:
   ```text
   https://<your-tunnel-host>
   ```
3. Deployed staging API:
   ```text
   https://<staging-api-host>
   ```

The app persists the base URL with `UserDefaults`, so changing the server does not require a
rebuild.

## App flow

1. Open the app.
2. Enter the API base URL.
3. Tap **Check /health + /models**.
4. Confirm `response_surrogate available`.
5. Enter `theta1`, `theta2`, and select `Case2`, `Case3`, or `Case4`.
6. Tap **Predict response**.
7. Review Type, confidence, Pt, max displacement, max force, probabilities, notes, and the
   force-displacement curve.

The **Mock** toolbar button loads the checked JSON fixture for offline UI preview.

## Build and test

Package/core checks:

```bash
cd ios/DDLaminateMVP
swift test
swift build
```

Optional iOS destination build from the repository root:

```bash
xcodebuild -project ios/DDLaminateMVPApp/DDLaminateMVPHost.xcodeproj \
  -scheme DDLaminateMVPHost \
  -destination 'generic/platform=iOS Simulator' build
```

If simulator runtimes or signing are unavailable, use `swift test` and `swift build` as the
minimum static/package verification.

## API contract used by the app

- `GET /health`
- `GET /api/v1/dd-laminate/models`
- `POST /api/v1/dd-laminate/predict/response`

MVP prediction payload:

```json
{
  "theta1": 30,
  "theta2": -30,
  "case": "Case2",
  "model": "response_surrogate"
}
```

Deferred endpoints:

- `POST /api/v1/dd-laminate/predict/theta`
- `POST /api/v1/dd-laminate/predict/curve`

CSV curve upload is intentionally deferred because native file selection and multipart UX are not
needed for the first iPhone MVP.
