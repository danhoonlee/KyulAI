# C2ES Laminate Android MVP

Native Android MVP for the same Laminate REST contract used by the iPhone app.

Implemented endpoint flow:

- `GET /health`
- `GET /api/v1/dd-laminate/models`
- `POST /api/v1/dd-laminate/predict/response`

The app checks API readiness automatically on launch and again before prediction. No separate connection button is required.

Run from Android Studio:

1. Open this directory: `android/DDLaminateMVP`
2. Sync Gradle
3. Select an emulator or Samsung device
4. Run `app`

Default API URL:

- `https://laminate.luvelox.com`

Development base URLs:

- Android emulator: `http://10.0.2.2:8000`
- Physical Android phone on the same Wi-Fi as the Mac: `http://<Mac LAN IP>:8000`
