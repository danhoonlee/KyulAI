# ImperialAX Injection Android MVP

Native Android MVP for the same Simple Injection REST contract used by the iPhone app.

Default API base URL:

- `https://injection.imperialax.com`

Endpoints used by the app:

- `GET /health`
- `GET /api/v1/simple-injection/models`
- `GET /api/v1/simple-injection/doe`
- `POST /api/v1/simple-injection/predict/sprue-pressure`

## Run

1. Open this directory in Android Studio: `android/InjectionMVP`
2. Let Gradle sync.
3. Select a phone or emulator.
4. Run the `app` configuration.

The app checks API readiness automatically. You can still edit the base URL field for a local server or a different tunnel.
