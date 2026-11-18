# RaceCam race control and endpoint provisioning contract (draft v1)

RaceDay Manager is the sole authority for official race decisions. Telemetry brokers distribute signed instructions; they do not create or alter decisions. Video and telemetry endpoints may share a host but remain logically independent.

## Pairing response (HTTPS, authenticated, single-use)
Return a versioned signed configuration with club_id, race_id, device_id, vessel_id, configuration_revision, expiry, primary/secondary telemetry MQTT 5 TLS endpoints, per-device MQTT credentials and scoped publish/subscribe topics, optional primary/standby video URLs and stream credentials, authoritative clock endpoint(s), race epoch, and initial start schedule. Never embed permanent credentials in QR payloads. Store secrets in Android Keystore-backed storage, not plaintext SharedPreferences. Require valid TLS hostnames and certificate chains.

## Race control MQTT topics
Suggested topics, to be ratified against the live telemetry server:
- race/{club_id}/{race_id}/devices/{device_id}/commands (device-specific)
- race/{club_id}/{race_id}/control (race-wide, read-only for phones)
- race/{club_id}/{race_id}/devices/{device_id}/acks (device acknowledgement)
- race/{club_id}/{race_id}/devices/{device_id}/gps (GPS observations)

MQTT QoS 1 for commands, acks and observations. ACLs prevent phones publishing control commands. Each command carries schema, race_id, epoch, revision, command_id, issued_at_ms, expires_at_ms, effective_at_ms, action, payload, signer identity and verifiable signature. Reject wrong race, expired commands, invalid signatures, stale epoch/revision, or conflicting commands. Deduplicate command_id. Acknowledge accepted/rejected with reason, device clock uncertainty, current configuration revision, and last GPS status. Retained broker messages are not an authority substitute.

## Timing
RaceDay Manager publishes an absolute UTC start instant, never a relative 'start in N seconds' instruction. The app estimates offset to an authenticated time source using repeated round-trip samples and monotonic Android elapsedRealtimeNanos. Estimate uncertainty from RTT, drift and age of last sync. The countdown and locally generated gun sound are scheduled against monotonic time derived from the authoritative UTC start. Ignore wall-clock jumps after scheduling; resync periodically and after network changes. Start signal is advisory until measured fleet skew meets race committee acceptance criteria. Show clock uncertainty, late command warnings and sync health. Avoid playing a retroactive gun if a start instruction arrives after its scheduled instant.

## Race officer last-minute changes
Officer app submits to RaceDay Manager via authenticated officer API, never directly to the broker. Manager validates officer role, issues a new signed revision and publishes it through telemetry. Actions include postpone, new_start, abandon, recall, course_change and notices. Phones apply only the highest valid authoritative revision and send acknowledgements; manager shows per-device receipt and uncertainty. A changed start cancels the prior pending gun atomically. A message received after effective_at_ms is marked late, not silently treated as timely.

## Video
Video config contains transport, primary URL, standby URL, stream identifier, credential lease and enabled flag. Video connection lifecycle must not gate GPS, timing or control. Existing local /h264 port 8088 remains available during migration. Server endpoint must be explicitly configured and verified; do not claim SRT upload is present in legacy camera app merely because an SRT URL is provisioned.

## Acceptance tests
1. Pair with separate telemetry and video hosts, and with combined host.
2. GPS continues while video disabled or unavailable.
3. Simulate staggered command delivery: all devices count down to same absolute start.
4. Measure A71 and other devices' clock offset/uncertainty and actual gun skew; test >2s divergence.
5. Officer postpones and reschedules at T-30s; old gun never fires.
6. Duplicate, reordered, expired, unsigned and wrong-race commands rejected.
7. Broker disconnect/reconnect and endpoint failover retain last valid start, with degraded-clock warning.
8. RaceDay Manager displays acknowledgement coverage and failed devices.
9. Verify certificate validation, scoped ACLs, replay prevention and credential revocation.

Status: specification only; pairing, command subscription, signed verification, sync engine, gun playback, video uplink and end-to-end acceptance tests are NOT implemented by this document.
