# Sailing-UK Signal Logger

Standalone Android field survey application, separate from RaceCam video capture and receiver.

## Status
- v0.3 field-test was built on SAGE and installed on Samsung A71 (SM-A715F, Android 13).
- Confirmed: timestamped CSV sampling every five seconds, network-derived position, Wi-Fi detection, Android foreground service, and samples while screen off.
- Not yet confirmed: GNSS satellite fix, 4G/5G RSRP/RSRQ/SINR, long-duration background stability.
- Not yet implemented: active upload speed testing, configurable data cap, Android CSV sharing.

## Privacy
All samples stay in app-local external storage. No GPS or measurements are transmitted by this build. Upload speed testing must only send synthetic data to explicitly configured HTTPS endpoints, with a user-controlled cap and no GPS payload.

## Build
Android Gradle Plugin 8.13.2, Java 17, compile SDK 35, min SDK 29, target SDK 35.
Run `gradle :app:assembleDebug` with an appropriate Gradle distribution and Android SDK.

## Test
1. Grant precise location and phone state permission; notifications optional.
2. Start survey outdoors. Check persistent foreground notification.
3. Verify CSV samples with screen on and off; check age and accuracy of location.
4. Repeat with Wi-Fi disabled and mobile data enabled, without disabling device security.
5. Do not interpret missing radio measurements as zero signal.

No APK is published from this branch yet; source is under development.
