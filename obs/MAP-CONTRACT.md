# RaceCam OBS map contracts

Two independent browser sources, never one map with a switchable handicap overlay:

1. **On-water map**: yacht markers at GNSS latitude/longitude. Show fix age and accuracy, label stale data clearly. No inferred locations.
2. **Handicap-adjusted race map**: race-progress display based on the same telemetry plus the **approved** RaceDay Manager entry list, start/finish times, club handicap method and race configuration. It is NOT a transformed latitude/longitude map. Do not fabricate a physical position from handicap calculations.

## Live data source
Internal receiver: `GET http://127.0.0.1:8789/api/race/positions` (loopback only). This endpoint is not publicly exposed.

Example:
```json
{"generated_ms":1794761447144,"positions":[{"camera_id":"cam-example","race_id":"race-1","fix_ms":1794761440000,"received_ms":1794761440100,"latitude":53.48,"longitude":-3.06,"accuracy_m":5,"sog_mps":3,"cog_deg":140,"age_ms":7144,"stale":false}]}
```

The OBS bridge must authenticate to a private race control API; never expose camera IDs, exact locations or club member names on the public internet by default. Authorised OBS instances can receive a read-only stream. User-configurable broadcast visibility and retention apply.

## RaceDay Manager integration
RaceDay Manager is authoritative for race_id, vessel identity, approved handicap, handicap algorithm, start signal, elapsed time, finish times, disqualifications and club points. The telemetry receiver is authoritative only for observed GNSS fixes. Synchronise a signed/versioned race snapshot to the OBS controller; cache last approved snapshot with explicit staleness status if RaceDay Manager is temporarily offline.

## Display rules
- Position freshness threshold currently 15 seconds; accuracy warning above 50 metres.
- GNSS time and receiver time remain distinct.
- Out-of-order offline replay must not move a yacht backwards on the live display.
- No finish detection based on a single GPS point without configured start/finish geometry and uncertainty handling.
- For handicap-adjusted display, indicate **provisional** until results are confirmed.
- If RaceDay Manager is unavailable, physical map remains usable; adjusted map shows 'handicap data unavailable' rather than invented ranks.
- Each OBS scene is independently addressable, e.g. `/obs/water` and `/obs/handicap` after an authenticated OBS bridge exists.

## Deployment status
Contract only; no OBS bridge, web map renderer or handicap ranking implementation is deployed yet.
