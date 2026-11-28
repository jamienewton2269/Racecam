# RaceDay Manager signed invitations — Android compatibility

This branch adds a **schema v1 verification-only** Android module and deliberately does **not** implement an invented enrollment protocol.

## Authoritative upstream files

- [raceday/invitations.py](https://github.com/jamienewton2269/RaceDay-Manager/blob/main/raceday/invitations.py)
- [tests/test_invitations.py](https://github.com/jamienewton2269/RaceDay-Manager/blob/main/tests/test_invitations.py)
- [CLIENT_PROVISIONING_CONTRACT.md](https://github.com/jamienewton2269/RaceDay-Manager/blob/main/docs/CLIENT_PROVISIONING_CONTRACT.md)

At implementation time upstream `invitations.py` blob SHA: `cc9074be3df2e6b38de11c41c2a8d50dd79ab65e`.

The exact envelope is `{"payload":...,"signature":"...","algorithm":"Ed25519"}`.
Signature input is the payload canonicalised using Python `json.dumps(sort_keys=True,separators=(',', ':'),ensure_ascii=False).encode('utf-8')`.
Signature is 64 bytes, URL-safe Base64 **without padding**. Issuer public keys must be installed independently of the QR payload and selected by `issuer_key_id`.

Schema v1 has exactly the fields currently declared in `raceday/invitations.py`, with `purpose="race-configuration-only"`. **It grants no MQTT access and cannot enroll a client certificate.** No invitation must be promoted to authorization absent a manager-side issuance ledger and trusted provisioning endpoint.

## Planned integration gate

The manager must publish schema revision, device identity and constraints, primary/secondary broker FQDNs, HTTPS enrollment API, TLS trust chain, certificate identity binding and renewal/revocation policy. Add golden cross-language fixtures signed by the manager and test tampered/expired/wrong-issuer inputs and replay.

The current standalone A71 telemetry and camera APKs stay installed. No username/password compatibility mode will be added. Client MQTT authentication must ultimately be TLS-only with a non-exportable Android Keystore private key.

## Physical A71 regression test — 2026-11-28

The Galaxy A71 (SM-A715F), running Android 13, lacks a usable platform `Ed25519` KeyFactory. The verifier therefore uses Bouncy Castle's lightweight Ed25519 API, pinned to `org.bouncycastle:bcprov-jdk18on:1.87`, rather than relying on the Android platform's removed/partial provider.

Official dependency: https://central.sonatype.com/artifact/org.bouncycastle/bcprov-jdk18on/1.87

Verified Maven Central SHA-256: `12d2d3dd82a9ec15e92ec7c7943ee64f6097c6dc12c07e984f1693b77565b9aa`.

The **test-only** APK sources and manual build script are in `android/telemetry/tests/android-smoke`. On SAGE, download the pinned JAR from Maven Central and verify its hash before running `build.cmd`.

On 2026-11-28 the independent test APK `org.sailinguk.racecam.invitesmoketest` compiled and installed on the physical A71. Android logcat reported:

```
PASS valid manager-format signature
PASS changed yacht rejected
PASS untrusted issuer rejected
PASS expired invitation rejected
PASS unsupported purpose rejected
```

The signature fixture was produced with Python `cryptography`, canonical payload sorted with `ensure_ascii=False`, and includes the Unicode yacht identifier `yacht-\u00e9`. Its public key is **test-only** and must never be used as a trusted production issuer. The fixture is not a genuine club signing key.

This validates the **verification primitive** only. No QR scanning, production trust establishment, issuance ledger, Android Keystore enrollment, TLS client certificate, MQTT broker commissioning or background GPS was tested. Integration awaits the published manager-side extended provisioning schema and certificate enrollment API. Do not change or publish the existing telemetry/video APKs solely for this test.
