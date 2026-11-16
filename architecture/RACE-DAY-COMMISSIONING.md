# Sailing-UK race-day commissioning contract — v1

Status: agreed architecture; implementation and deployment are not yet complete.

## Authority and responsibilities

- **RaceDay Manager** is the sole authority for club/race identity, vessel assignment, handicap method, official start and race decisions. It commissions and monitors services but is not a high-volume media or GPS relay.
- **Telemetry nodes** independently ingest authenticated GNSS observations, retain an append-only observation history and exchange observations and camera authorisation state. Default: two active nodes; single node remains supported.
- **MediaMTX** receives/distributes SRT video, independently of GPS. Default: primary and standby, with active/active selectable. Do not assume MediaMTX replicates video.
- **OBS controller** translates authorised RaceDay Manager requests into OBS WebSocket scene changes. The physical clubhouse OBS computer keeps its current scene during control outages.
- **Visualisation** provides separate actual-position and handicap-adjusted views. Only RaceDay Manager may approve handicap calculations.

## Commissioning sequence

1. Operator selects club, race, vessels and desired musicians.
2. RaceDay Manager discovers/provisions endpoints and verifies HTTPS identity, capabilities, clock skew, storage, reachability, authentication, and replication status.
3. Issue a signed, versioned **race commissioning manifest** with a unique race/epoch ID and expiry. Nodes cache the last valid manifest for operation during conductor outages.
4. Synchronise device credentials and revocation state to both telemetry nodes **before** issuing QR pairing sessions. Replication must be tested, not assumed.
5. QR contains a short-lived, single-use pairing reference and HTTPS bootstrap address only. Never encode permanent secrets or DDNS API keys.
6. Android verifies TLS, exchanges pairing reference for device-specific credentials and signed configuration: vessel/race assignment; both telemetry URLs; optional video primary/standby URLs and stream credentials; server health policy; start time; configuration version.
7. Android sends GPS independently of video. Default dual-send to both telemetry endpoints with identical camera ID, session ID, sequence, fix timestamp and fix payload.
8. MediaMTX default: one active publisher destination, secondary preconfigured for failover. Duplicate video publishing is optional and must be tested against handset uplink and receiver capacity.
9. OBS controller receives authorised scene/map choices and uses independently configured OBS WebSocket access.
10. RaceDay Manager shows per-musician health, pairing status, replication lag, GPS freshness, video availability and OBS acknowledgements.

## Replication rules

- GPS is an observation, not an authoritative race decision. Each node persists observations before acknowledgement and asynchronously replicates immutable observation IDs.
- Stable observation key: (camera_id, session_id, sequence). Same key with different payload is a conflict and must be flagged; never silently overwrite.
- Keep fix timestamp, receive timestamp and source node separately. Late or out-of-order observations may be retained as history but must not displace a newer live position.
- Each node accepts observations when isolated; reconciliation is eventual. **Two nodes cannot provide quorum-based split-brain protection on their own.**
- Official race configuration, camera assignments and revocations require a single authoritative signed/versioned manifest from RaceDay Manager; isolated nodes must not independently edit it.
- Revocation has a security tradeoff during partition: stale offline nodes might not receive an urgent revocation. Use short-lived credentials/manifest leases and explicitly flag this risk; fail closed when credentials expire.
- Do not call replication complete until both nodes are exercised with partitions, rejoin, duplicate and conflicting fixes.

## Failure behaviour

- RaceDay Manager unavailable: existing authenticated ingest, video and OBS scene continue under last valid unexpired configuration; no new official race decisions.
- Telemetry A or B unavailable: other node continues receiving; client marks degraded state and retries; reconcile on recovery.
- Both telemetry nodes unavailable: phone may retain a bounded local buffer with clear expiry and user consent; not yet implemented.
- MediaMTX primary unavailable: phone reconnects to standby; expect interruption unless simultaneous publishing is enabled.
- OBS controller unavailable: OBS retains scene and permits authorised local control.
- Club WAN unavailable: local services continue where connected; phones offshore may lose connectivity.

## Acceptance criteria

- A71 paired once; QR reuse rejected; correct yacht/race association on both telemetry nodes.
- GPS-only session works with MediaMTX disabled.
- Identical observations on both telemetry nodes deduplicate correctly.
- Isolate A, isolate B, restore connectivity: no data loss for acknowledged observations within the tested durability policy; replication converges.
- Replay old observation after new one: live map does not move backwards.
- Revoke device, expire leases and partition one node: document and verify behaviour.
- Video failover tested separately from telemetry.
- OBS controller fail/restart does not terminate ongoing stream.
- No public access to receiver administrative, telemetry history or OBS control endpoints.

## Current implementation gap

LXC 270 has one tested GPS ingest service and one status service. No dual-node replication, commissioning manifest, complete QR provisioning, Android GPS integration, RaceDay Manager orchestration or dual MediaMTX failover is verified deployed. This document is the contract for implementing those features incrementally without disrupting the existing receiver.
