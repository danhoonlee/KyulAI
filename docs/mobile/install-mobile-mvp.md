# ImperialAX Laminate Mobile MVP Install Notes

## iPhone

For a private MVP, install from Xcode first. TestFlight/App Store can come later.

1. Open `ios/DDLaminateMVPApp/DDLaminateMVPHost.xcodeproj`.
2. Select the `DDLaminateMVPHost` scheme.
3. Connect the iPhone with USB, trust the Mac, and select the iPhone as the run destination.
4. In Signing & Capabilities, select your Apple ID team.
5. Press Run.

The default mobile API base URL is:

```text
https://laminate.imperialax.com
```

For local development, the API base URL must be reachable from the phone:

- Same Wi-Fi: `http://<Mac LAN IP>:8000`
- Public/shareable MVP: an HTTPS tunnel or deployed API URL

`127.0.0.1` only works for the iOS simulator.

## Android

Open `android/DDLaminateMVP` in Android Studio.

1. Install Android Studio if needed.
2. Enable Developer Options and USB debugging on the Samsung phone.
3. Connect the phone with USB and allow debugging.
4. Open `android/DDLaminateMVP`.
5. Let Android Studio sync Gradle.
6. Select the phone and press Run.

The default Android API base URL is:

```text
https://laminate.imperialax.com
```

For Android local development:

- Physical Samsung phone: `http://<Mac LAN IP>:8000`
- Android emulator: `http://10.0.2.2:8000`

The MVP enables cleartext HTTP for local development. For real distribution, use HTTPS and remove broad cleartext access.
