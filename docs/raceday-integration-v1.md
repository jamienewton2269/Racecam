# RaceDay Manager → RaceCam race snapshot (draft v1)

RaceDay Manager owns competitor entries, yacht identities, handicap values and scoring rules. RaceCam consumes a read-only, authenticated, versioned snapshot. No separate editable handicap database on the receiver.

## Endpoint
GET /api/v1/races/{race_id}/snapshot
- HTTPS only; dedicated least-privilege receiver credential; no membership personal details beyond approved racing display names.
- ETag/If-None-Match supported; snapshots signed or authenticated end-to-end, validated before use.
- Explicit UTC timestamps, immutable snapshot_id and monotonically increasing revision.
- Never silently replace a race's active locked snapshot after its start.

## Example schema (illustrative, not real competitors)
```json
{
  "schema_version": 1,
  "race_id": "example-race",
  "revision": 3,
  "snapshot_id": "example-race-r3",
  "issued_at_utc": "2026-11-15T12:00:00Z",
  "start_at_utc": "2026-11-15T12:15:00Z",
  "handicap": {
    "method": "time_on_time",
    "rule_id": "example-club-rule",
    "rule_version": "1",
    "projection_method": "estimated_remaining_time",
    "units": "dimensionless"
  },
  "course": {
    "course_id": "example-course",
    "revision": 1,
    "marks": []
  },
  "entries": [
    {
      "entry_id": "entry-001",
      "yacht_id": "yacht-001",
      "display_name": "Example Yacht",
      "camera_id": "cam-example",
      "rating": "0.9500"
    }
  ]
}
```

## Rules
1. Resolve Android camera_id → yacht_id → race entry; reject ambiguous/unregistered mappings.
2. Store exact rating decimal and rule version. Do not assume all clubs use time-on-time.
3. Snapshot validation is atomic: require unique IDs, known method, valid positive ratings, coherent UTC start, ordered course marks and required fields. Unknown methods must fail closed, not silently default.
4. Lock the active snapshot at start. Subsequent changes are staged and require explicit authorised race-officer application with audit history.
5. Cache the last verified snapshot locally for offline continuation; show snapshot revision and freshness.
6. Actual-position map never applies handicap. Handicap map uses the locked race snapshot and clearly labels projected positions and prediction uncertainty.
7. Starting-gun phones receive the same absolute UTC start from the approved snapshot, with a separately signed/versioned postponement or cancellation. A disconnected phone must warn about potentially stale instructions.
8. Official finish timestamps remain recorded separately; RaceDay Manager alone approves official corrected results.
9. Keep video streaming independent of snapshot availability.
10. No live deployment until integration tests, authentication review and Android timing measurements pass.

## Tests required
- Matching camera/yacht IDs; duplicate entries; unknown ratings; schema downgrade
- ETag no-change and revised snapshot; invalid/expired credentials
- Offline receiver with validated cache; failed partial refresh
- Start-time lock and authorised change; disconnected-phone postponement
- Actual map unaffected by handicap updates; handicap projection recalculated after approved revision
- Race start sound spread measured acoustically across devices (target ≤2000 ms)
