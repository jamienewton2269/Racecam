# Android A71 integration and acceptance checklist

## Current state (2026-11-15)
- `RaceCamTelemetrySender.java` is committed as a transport component, **not integrated into the installed A71 APK**.
- Receiver telemetry service (LXC 270, loopback 8788) and status service (loopback 8789) are running.
- A temporary registered-camera integration test passed: valid fix accepted, duplicate rejected, revoked camera hidden from status feed.
- HTTPS external reverse proxy and QR provisioning are not configured.
- Do not change MediaMTX or enable SRT as part of GPS work.

## Android integration
1. Use existing camera app package `org.sailinguk.racecam` and existing GNSS `LocationManager` / `FusedLocationProviderClient` callback. Do not create a second location listener if one already exists.
2. After authorised pairing, persist camera ID and camera secret in Android Keystore-backed encrypted storage. Never put secrets in QR codes, logcat, intents, plain SharedPreferences, or Git.
3. Construct `RaceCamTelemetrySender(httpsReceiverBase, cameraId, secret, listener)` once for the active session.
4. Call `sender.submit(location, raceId, batteryPercent, cameraStatus)` on new location fixes. The sender uses `Location.getTime()` (UTC milliseconds) and GNSS-reported accuracy.
5. Close sender when the race camera session stops. Respect foreground service/background location permission rules; location sharing must be visible and consented.
6. Server endpoint `/api/telemetry` must be HTTPS with a trusted certificate. Do not bypass Android TLS verification.
7. Do not assume Android pairing is complete until a valid QR flow and server certificate validation are implemented.

## Receiver deployment prerequisites
- Provide public HTTPS host per club; route only `POST /api/pair` and `POST /api/telemetry` to the respective local services.
- Admin pairing endpoint `/admin/pairings` and internal `/api/race/positions` must remain private.
- Configure rate limits and request size limits at reverse proxy; restrict receiver egress and firewall appropriately.
- `RACECAM_PUBLIC_URL` must be a verified HTTPS URL before generating a QR pairing session.
- Verify MediaMTX SRT stream ID and callback payload against installed MediaMTX v1.21.3 before enabling SRT.

## Live test criteria
- Pair A71 to test receiver using a one-use QR code; verify second use is rejected.
- Record GNSS latitude, longitude, UTC fix time, accuracy, SOG, COG at approximately 1 Hz.
- Verify HTTPS response 202 and the same fix appears on loopback status feed.
- Disable video only: GPS must continue.
- Disconnect mobile data: sender must not leak secrets or block UI; reconnect and verify new fixes.
- Revoke camera: both telemetry and video publishing must be rejected.
- Ensure stale fixes (>15 s) and poor accuracy (>50 m) are flagged on the physical-position map.
- Do not use handicap-adjusted rankings until RaceDay Manager provides approved club rules, entry list and race start time.

## Important limitation
The Android source is a starting transport implementation. Its queue policy intentionally favours recent fixes over historical replay; offline fix buffering is not yet implemented. Do not describe delayed replay from the Android phone as a completed feature.
