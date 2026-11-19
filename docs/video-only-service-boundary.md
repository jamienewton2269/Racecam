# RaceCam video receiver: service boundary

The RaceCam receiving server is **video only**. The separate Race Telemetry Server
is the authoritative ingest endpoint for GPS, LoRa and other yacht-position data.

## Permitted on the video receiver
- MediaMTX receiving authenticated camera video (SRT).
- Camera pairing and revocation for **video publishing**.
- Video stream health, camera identity, and OBS-compatible output.
- Video-specific diagnostics without geographic coordinates.

## Prohibited on the video receiver
- GPS fixes, latitude/longitude, speed/course, NMEA or LoRa telemetry ingestion.
- Telemetry databases, position APIs or race-position map generation.
- A reverse-proxy route to a GPS ingest service.
- Starting or enabling `racecam-telemetry.service` or `racecam-status.service`.

## Existing code preservation
Legacy `racecam-receiver/telemetry.py`, `status.py`, their systemd units
and live GPS integration tests remain in Git history pending **verified**
migration to the dedicated telemetry repository. They must **not** be installed
by the video receiver installer. Do not delete them until destination parity
and migration tests are confirmed.

## Deployment gate
1. Inspect actual deployed units and reverse-proxy routes on CT270.
2. Back up installed configuration and database before any change.
3. Verify the pairing service and MediaMTX remain functional.
4. Confirm video-only installer does not deploy GPS services.
5. Test Android H.264 -> SRT -> MediaMTX -> OBS, including revoke/reconnect.
6. Remove legacy GPS services from CT270 **only after** verifying the separate
   telemetry server is operational and preserving any required data.

## Shared identity, not shared data paths
RaceDay Manager maps the yacht and its camera/telemetry device IDs.
It can correlate a video feed with a yacht's telemetry, but the GPS data must
flow directly from the mobile app or LoRa gateway to the telemetry server.
