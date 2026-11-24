package org.sailinguk.racecam;
import org.json.JSONObject;

/** Serialises verification and application; transport must acknowledge only after acceptance. */
public final class RaceCommandController {
    private final RaceStartClock clock;
    private final RaceControlVerifier verifier;
    public RaceCommandController(RaceStartClock clock,RaceControlVerifier verifier){
        this.clock=clock;this.verifier=verifier;
    }
    public synchronized JSONObject receive(String envelope) throws Exception {
        JSONObject cmd=verifier.verify(envelope,clock.trustedUtcMs());
        String action=cmd.getString("action");
        long revision=cmd.getLong("revision");
        if("course_change".equals(action)||"notice".equals(action))
            throw new UnsupportedOperationException("No course or notice handler installed");
        long start=0;
        if("start".equals(action)||"new_start".equals(action))
            start=cmd.getJSONObject("payload").getLong("start_utc_ms");
        if(!clock.apply(cmd.getString("epoch"),revision,cmd.getString("command_id"),action,start))
            throw new SecurityException("Scheduler rejected command");
        verifier.applied(revision);
        return new JSONObject().put("command_id",cmd.getString("command_id"))
            .put("revision",revision).put("status","applied");
    }
}
