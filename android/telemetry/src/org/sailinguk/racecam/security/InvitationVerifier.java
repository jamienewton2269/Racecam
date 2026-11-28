package org.sailinguk.racecam.security;

import org.json.JSONObject;
import java.nio.charset.StandardCharsets;
import java.security.KeyFactory;
import java.security.PublicKey;
import java.security.Signature;
import java.security.spec.X509EncodedKeySpec;
import java.time.Duration;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.Arrays;
import java.util.Base64;
import java.util.Iterator;
import java.util.Map;
import java.util.TreeMap;

/**
 * Verifies RaceDay Manager configuration-only invitations (schema v1).
 * Mirrors raceday/invitations.py on RaceDay-Manager main.
 * This verifier does NOT authorise device enrollment or MQTT access.
 */
public final class InvitationVerifier {
    private InvitationVerifier() {}
    private static final byte[] ED25519_SPKI = {
        0x30, 0x2a, 0x30, 0x05, 0x06, 0x03, 0x2b, 0x65, 0x70, 0x03, 0x21, 0x00
    };
    private static final String[] FIELDS = {
        "club_id", "course_revision", "event_id", "expires_utc",
        "invitation_id", "issued_utc", "issuer_key_id", "purpose",
        "race_id", "schema_version", "start_utc", "yacht_id"
    };
    public interface TrustedIssuerKeys {
        /** Trusted 32-byte raw Ed25519 key installed independently of the QR invitation. */
        byte[] lookup(String issuerKeyId);
    }

    public static JSONObject verify(String json, TrustedIssuerKeys trusted, Instant now) throws Exception {
        if (trusted == null || now == null) throw new SecurityException("Trusted keys and clock required");
        JSONObject envelope = new JSONObject(json);
        if (envelope.length() != 3 || !envelope.has("payload")
                || !envelope.has("signature") || !"Ed25519".equals(envelope.optString("algorithm")))
            throw new SecurityException("Unsupported invitation envelope");
        JSONObject payload = envelope.getJSONObject("payload");
        String keyId = payload.getString("issuer_key_id");
        byte[] rawKey = trusted.lookup(keyId);
        if (rawKey == null || rawKey.length != 32) throw new SecurityException("Untrusted issuer");
        byte[] encoded = Arrays.copyOf(ED25519_SPKI, ED25519_SPKI.length + 32);
        System.arraycopy(rawKey, 0, encoded, ED25519_SPKI.length, 32);
        PublicKey key = KeyFactory.getInstance("Ed25519").generatePublic(new X509EncodedKeySpec(encoded));
        byte[] signature = signatureBytes(envelope.getString("signature"));
        Signature verifier = Signature.getInstance("Ed25519");
        verifier.initVerify(key);
        verifier.update(canonical(payload).getBytes(StandardCharsets.UTF_8));
        if (!verifier.verify(signature)) throw new SecurityException("Invalid invitation signature");
        if (payload.length() != FIELDS.length) throw new SecurityException("Unsupported invitation fields");
        for (String field : FIELDS)
            if (!payload.has(field) || payload.isNull(field)) throw new SecurityException("Missing " + field);
        if (payload.getInt("schema_version") != 1 ||
                !"race-configuration-only".equals(payload.getString("purpose")))
            throw new SecurityException("Unsupported invitation purpose");
        for (String field : new String[]{"club_id", "event_id", "race_id", "yacht_id", "issuer_key_id"}) {
            String value = payload.getString(field);
            if (value.trim().isEmpty() || value.length() > 128)
                throw new SecurityException("Invalid " + field);
        }
        if (payload.getString("invitation_id").isEmpty())
            throw new SecurityException("Missing invitation ID");
        Instant issued = OffsetDateTime.parse(payload.getString("issued_utc")).toInstant();
        Instant expiry = OffsetDateTime.parse(payload.getString("expires_utc")).toInstant();
        OffsetDateTime.parse(payload.getString("start_utc"));
        if (!now.isBefore(expiry) || issued.isAfter(now.plus(Duration.ofMinutes(5))))
            throw new SecurityException("Expired or not-yet-valid invitation");
        return payload;
    }

    private static byte[] signatureBytes(String input) {
        if (!input.matches("[A-Za-z0-9_-]{86}"))
            throw new SecurityException("Invalid unpadded URL-safe signature");
        byte[] bytes = Base64.getUrlDecoder().decode(input + "==");
        if (bytes.length != 64 ||
                !Base64.getUrlEncoder().withoutPadding().encodeToString(bytes).equals(input))
            throw new SecurityException("Invalid signature encoding");
        return bytes;
    }

    /** Python json.dumps(sort_keys=True,separators=(',', ':'),ensure_ascii=False), v1 scalar types. */
    private static String canonical(JSONObject payload) throws Exception {
        TreeMap<String,Object> sorted = new TreeMap<>();
        Iterator<String> it = payload.keys();
        while (it.hasNext()) {
            String key = it.next();
            sorted.put(key, payload.get(key));
        }
        StringBuilder b = new StringBuilder("{");
        for (Map.Entry<String,Object> entry : sorted.entrySet()) {
            if (b.length() > 1) b.append(',');
            quoted(b, entry.getKey());
            b.append(':');
            Object value = entry.getValue();
            if (value instanceof String) quoted(b, (String)value);
            else if (value instanceof Integer || value instanceof Long || value instanceof Boolean)
                b.append(value.toString());
            else throw new SecurityException("Unsupported v1 canonical JSON value");
        }
        return b.append('}').toString();
    }
    private static void quoted(StringBuilder b, String s) {
        b.append('"');
        for (int i = 0; i < s.length(); ++i) {
            char c = s.charAt(i);
            if (c == '"' || c == '\\') b.append('\\').append(c);
            else if (c == '\b') b.append("\\b");
            else if (c == '\f') b.append("\\f");
            else if (c == '\n') b.append("\\n");
            else if (c == '\r') b.append("\\r");
            else if (c == '\t') b.append("\\t");
            else if (c < 0x20) {
                String hex = Integer.toHexString(c);
                b.append("\\u");
                for (int pad = hex.length(); pad < 4; ++pad) b.append('0');
                b.append(hex);
            } else b.append(c);
        }
        b.append('"');
    }
}
