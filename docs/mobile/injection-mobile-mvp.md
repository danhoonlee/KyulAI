# KyulAI Injection Mobile MVP

This MVP provides native iPhone and Android clients for the Simple Injection API.

## API

Default base URL:

```text
https://injection.imperialax.com
```

Endpoints used by both apps:

- `GET /health`
- `GET /api/v1/simple-injection/models`
- `GET /api/v1/simple-injection/doe`
- `POST /api/v1/simple-injection/predict/sprue-pressure`

The apps check `/health`, `/models`, and `/doe` automatically on launch. The base URL remains editable for local servers or tunnels.

## iPhone

Project paths:

- Swift package: `ios/InjectionMVP`
- Xcode host app: `ios/InjectionMVPApp/InjectionMVPHost.xcodeproj`

Run:

1. Open `ios/InjectionMVPApp/InjectionMVPHost.xcodeproj` in Xcode.
2. Select the `InjectionMVPHost` scheme.
3. Select an iPhone Simulator or a connected iPhone.
4. Press Run.

For a real iPhone, use bundle ID `com.kyulai.injection` and select your Apple development team in Signing & Capabilities.

## Android

Project path:

- `android/InjectionMVP`

Run:

1. Open `android/InjectionMVP` in Android Studio.
2. Let Gradle sync.
3. Select a Samsung/Android device or emulator.
4. Run the `app` configuration.

Android package/application ID:

```text
com.kyulai.injection
```

## Implemented Scope

- API readiness check without a manual connect button
- DOE geometry/process loading
- Sprue pressure prediction request
- Peak pressure/time result display
- Pressure curve chart with peak marker
- Filling pressure summary display
- Injection app icon applied to iOS and Android

## Verification

Completed locally:

- `swift test` in `ios/InjectionMVP`
- `xcodebuild -project ios/InjectionMVPApp/InjectionMVPHost.xcodeproj -scheme InjectionMVPHost -destination generic/platform=iOS\ Simulator build`
- `xmllint --noout android/InjectionMVP/app/src/main/AndroidManifest.xml`
- Public API smoke test against `https://injection.imperialax.com`

Android APK build was not run locally because this machine does not currently expose `gradle`, `gradlew`, or `kotlinc`.
