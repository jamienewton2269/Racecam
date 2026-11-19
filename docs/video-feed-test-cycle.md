# Video-only feed test cycle (CT270)

Run this only after confirming MediaMTX SRT is configured and the temporary test
camera is paired and authorized. The script does **not** modify MediaMTX, systemd,
firewall, DNS or production streams, and does not send GPS.

## Prerequisites
- `ffmpeg` and `ffprobe` installed on the test machine.
- A temporary camera identity authorized to publish on a dedicated MediaMTX path.
- SRT publish and RTSP playback URLs verified against the deployed MediaMTX
  configuration. Do not assume a stream-ID syntax without inspecting the running
  version and authentication configuration.
- Receiver's RTSP playback port accessible from the test machine; prefer loopback
  execution on CT270. Avoid exposing RTSP publicly.

## Execute
Set `RACECAM_TEST_SRT_URL` to the **complete authenticated SRT URL** for the
temporary camera, and `RACECAM_TEST_RTSP_URL` to the corresponding RTSP URL.
Use environment variables, not committed credentials. Run:

```sh
bash racecam-receiver/test_srt_video_feed.sh
```

The script publishes a synthetic 1280x720, 25 fps H.264 MPEG-TS stream over
SRT and probes the resulting RTSP video codec and dimensions. It cleans up its
temporary files and publisher process. The test runs for 12 seconds by default.

## Acceptance matrix
1. Authorized synthetic H.264 SRT publish -> RTSP H.264 1280x720 probe PASS.
2. Invalid camera credential -> SRT publish rejected.
3. Revoked camera -> new publish rejected (existing session teardown tested separately).
4. Restart MediaMTX -> authorized publisher reconnects without manual changes.
5. Android A71 H.264 -> SRT -> MediaMTX -> OBS shows live motion.
6. Concurrent cameras use distinct paths; no camera can publish to another path.
7. No telemetry service, position API or GPS database is used by any video test.

Do not claim completion until test logs/OBS playback are observed on the
actual receiver. Never paste permanent stream secrets into GitHub issues or logs.
