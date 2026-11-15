# RaceCam Receiver

Open-source multi-club sailing camera receiver development.

## Current deployment
- Test receiver: LXC 270 (bsc-race-test) on Node B
- Existing MediaMTX: v1.21.3
- Active RTSP: 127.0.0.1:8554
- SRT authenticated configuration is **staged, not activated**
- Receiver pairing service v0.9 is **not yet installed**

## Security
Do not commit admin tokens, camera passwords, generated environment files, SQLite databases, DDNS API keys, or club-specific credentials.

## Status
Repository initialization only. The tested v0.9 source archive has **not yet been committed**. Do not run any installer until source integrity is verified.

## Intended acceptance tests
1. Install pairing service on loopback under dedicated system account.
2. Verify health, unknown-camera rejection, authorized publishing, and revocation.
3. Enable MediaMTX SRT with external HTTP authentication only after successful tests.
4. Test Android A71 H.264-to-SRT-to-OBS streaming.
