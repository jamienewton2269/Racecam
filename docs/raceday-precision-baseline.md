# RaceDay Precision — Android-only baseline

Status: design and implementation plan; not yet deployed or tested.

## Constraints
- Use existing Android phones; no yacht-mounted additional hardware.
- Preserve existing RaceCam video, GPS telemetry and QR provisioning.
- RaceDay Manager controls race assignment; telemetry receivers remain independently deployable.
- No LoRa, RTK hardware or shore station required for baseline.
- Never represent filtered/predicted positions as measured GNSS fixes.

## Phase 1: handset capability and raw data
- Detect Android API level, GNSS raw-measurement availability, supported constellations and carrier-frequency metadata where reported.
- Capture Android Location latitude, longitude, elapsedRealtimeNanos, UTC timestamp, horizontal accuracy (with availability flag), speed, bearing, speed/bearing accuracy if available, and provider.
- Optionally register GnssMeasurementsEvent.Callback; collect satellite count, constellation, C/N0, carrier frequency and clock quality only where exposed.
- Do not assume raw GNSS support, dual frequency, carrier phase or correction acceptance.
- Respect Android foreground location service and permissions; report permission/battery limitations.

## Phase 2: telemetry compatibility
- Keep current telemetry schema unchanged until receiver contract is inspected.
- Add optional, versioned extension containing source fix, estimated fix, uncertainty, observation age, quality flags and algorithm version.
- Record source timestamps and receive timestamps independently; handle out-of-order packets and reconnects.
- Never mix a stale position with a fresh timestamp.
- Preserve existing video stream and telemetry endpoint assignment.

## Phase 3: filtering
- Begin with outlier diagnostics and a replayable baseline.
- Evaluate constant-velocity Kalman filter in local ENU coordinates with uncertainty-aware updates and conservative turn handling.
- Preserve raw track and compare filtered track against independent reference; quantify latency and positional error.
- Do not claim improved absolute accuracy from smoothness alone.

## Phase 4: race operations
- Show GPS status, reported uncertainty, fix age and last successful telemetry receipt.
- Start-line calculations advisory only; no automated OCS decisions without verified accuracy, time sync and bow-offset handling.
- Record race replay with raw and processed positions.

## Acceptance gates
1. Existing RaceCam functions pass regression tests.
2. At least one Android device reports capability inventory and unmodified fixes.
3. Replay accepts recorded data deterministically.
4. Packet loss/reordering and GNSS outages cannot create false fresh fixes.
5. Compare accuracy and lag with independent surveyed/known reference and moving course.
6. Document measured performance by handset model, without promising sub-metre accuracy.

## Next implementation action
Inspect the current Android source tree, telemetry payload format and CI before changing application code. Implement a small feature-flagged capability probe and baseline logger first.
