package org.sailinguk.racecam;

import android.util.Base64;
import org.json.JSONObject;
import java.nio.charset.StandardCharsets;
import java.security.KeyFactory;
import java.security.PublicKey;
import java.security.Signature;
import java.security.spec.X509EncodedKeySpec;

/**
 * Verify RaceDay Manager commands BEFORE updating RaceStartClock.
 * Envelope: {"payload_b64":"...", "signature_b64":"..."}.
 * Signature: SHA256withECDSA over the exact UTF-8 payload bytes.
 * Public key is pinned from an independently authenticated provisioning channel.
 */
public final class RaceControlVerifier {
    private final PublicKey authority;
    private final String clubId, raceId, epoch;
    private long revision=-1;

    public RaceControlVerifier(String publicKeyDerBase64, String clubId,
                               String raceId, String epoch) throws Exception {
        byte[] der=Base64.decode(publicKeyDerBase64,Base64.DEFAULT);
        authority=KeyFactory.getInstance("EC").generatePublic(new X509EncodedKeySpec(der));
        this.clubId=clubId;this.raceId=raceId;this.epoch=epoch;
    }

    public synchronized JSONObject verify(String envelopeJson, long trustedUtcMs) throws Exception {
        JSONObject envelope=new JSONObject(envelopeJson);
        byte[] payload=Base64.decode(envelope.getString("payload_b64"),Base64.DEFAULT);
        if(payload.length>16384)throw new SecurityException("Command too large");
        byte[] signature=Base64.decode(envelope.getString("signature_b64"),Base64.DEFAULT);
        Signature verifier=Signature.getInstance("SHA256withECDSA");
        verifier.initVerify(authority);verifier.update(payload);
        if(!verifier.verify(signature))throw new SecurityException("Invalid signature");
        JSONObject cmd=new JSONObject(new String(payload,StandardCharsets.UTF_8));
        if(!clubId.equals(cmd.getString("club_id"))||
           !raceId.equals(cmd.getString("race_id"))||
           !epoch.equals(cmd.getString("epoch")))throw new SecurityException("Wrong race");
        long issued=cmd.getLong("issued_at_ms"),expires=cmd.getLong("expires_at_ms");
        if(issued>trustedUtcMs+2000 || expires<=trustedUtcMs ||
           expires<=issued)throw new SecurityException("Command outside validity window");
        long next=cmd.getLong("revision");
        if(next<=revision)throw new SecurityException("Stale or duplicate revision");
        String action=cmd.getString("action");
        if(!("start".equals(action)||"new_start".equals(action)||
             "postpone".equals(action)||"abandon".equals(action)||
             "recall".equals(action)||"course_change".equals(action)||
             "notice".equals(action)))throw new SecurityException("Unsupported action");
        if(cmd.getString("command_id").isEmpty())throw new SecurityException("Missing command ID");
        // Revision is committed by caller only after successful application.
        return cmd;
    }

    public synchronized void applied(long acceptedRevision) {
        if(acceptedRevision>revision)revision=acceptedRevision;
    }
}
