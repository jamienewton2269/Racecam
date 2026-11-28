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

**Runtime note:** `java.security.Signature.getInstance("Ed25519")` must be tested on the A71 Android version. If unavailable, integrate an audited provider before enabling QR imports; never skip signature verification.
