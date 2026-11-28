package org.sailinguk.racecam.smoketest;

import android.app.Activity;
import android.os.Bundle;
import android.util.Log;
import android.widget.TextView;
import org.json.JSONObject;
import org.sailinguk.racecam.security.InvitationVerifier;
import java.time.Instant;
import java.util.Base64;

/** Test-only app. No production credentials or signing keys. */
public final class TestActivity extends Activity {
    private static final String PUB = "iQRbd9bRm-Qmcv0c4z_cLfBsVhpSHpcVmGNRs7psL3k";
    private static final String SIGNATURE = "EmLARI0mHsBNZkc8reeNzYC8Cdb4wU0C4Jkx6RKwbbntunuqgACBoTu8PGYc8qZU5mDIr6BEpbF6ghYCl-6uBw";
    private static final Instant NOW = Instant.parse("2026-11-28T12:00:00Z");
    private final StringBuilder results = new StringBuilder();

    public void onCreate(Bundle state) {
        super.onCreate(state);
        try {
            JSONObject envelope = fixture();
            JSONObject verified = InvitationVerifier.verify(envelope.toString(), id -> "test-only-issuer".equals(id) ?
                    Base64.getUrlDecoder().decode(PUB) : null, NOW);
            check("valid manager-format signature", "yacht-é".equals(verified.getString("yacht_id")));
            JSONObject tampered = new JSONObject(envelope.toString());
            tampered.getJSONObject("payload").put("yacht_id", "yacht-two");
            rejection("changed yacht", tampered, id -> Base64.getUrlDecoder().decode(PUB), NOW);
            rejection("untrusted issuer", envelope, id -> null, NOW);
            rejection("expired invitation", envelope, id -> Base64.getUrlDecoder().decode(PUB), Instant.parse("2027-01-01T00:00:00Z"));
            JSONObject wrongPurpose = new JSONObject(envelope.toString());
            wrongPurpose.getJSONObject("payload").put("purpose", "device-enrollment");
            rejection("unsupported purpose", wrongPurpose, id -> Base64.getUrlDecoder().decode(PUB), NOW);
        } catch (Exception e) {
            results.append("FAIL exception: ").append(e.getClass().getSimpleName()).append(" ").append(e.getMessage()).append("\n");
        }
        String report = results.toString();
        Log.i("RaceInviteTest", report.replace("\n", " | "));
        TextView view = new TextView(this);
        view.setTextSize(18);
        view.setPadding(30, 60, 30, 20);
        view.setText(report);
        setContentView(view);
    }
    private void check(String name, boolean ok) {
        results.append(ok ? "PASS " : "FAIL ").append(name).append("\n");
    }
    private void rejection(String name, JSONObject doc, InvitationVerifier.TrustedIssuerKeys trusted, Instant now) {
        try {
            InvitationVerifier.verify(doc.toString(), trusted, now);
            check(name + " rejected", false);
        } catch (SecurityException expected) {
            check(name + " rejected", true);
        } catch (Exception error) {
            results.append("FAIL ").append(name).append(" unexpected ").append(error.getClass().getSimpleName()).append("\n");
        }
    }
    private JSONObject fixture() throws Exception {
        JSONObject p = new JSONObject();
        p.put("schema_version", 1);
        p.put("invitation_id", "smoke-golden-001");
        p.put("club_id", "BSC");
        p.put("event_id", "test-event");
        p.put("race_id", "test-race");
        p.put("yacht_id", "yacht-é");
        p.put("issuer_key_id", "test-only-issuer");
        p.put("start_utc", "2026-12-01T10:00:00+00:00");
        p.put("expires_utc", "2026-12-31T10:00:00+00:00");
        p.put("issued_utc", "2026-11-28T12:00:00+00:00");
        p.put("course_revision", 1);
        p.put("purpose", "race-configuration-only");
        return new JSONObject().put("payload", p).put("signature", SIGNATURE).put("algorithm", "Ed25519");
    }
}
