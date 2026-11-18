package org.sailinguk.racecam;

import android.os.SystemClock;

/** Pure scheduling state for RaceDay Manager's absolute UTC start decisions.
 * An externally authenticated clock sync supplies the offset and uncertainty.
 * This class does not authenticate commands: callers MUST verify signature,
 * race/epoch, expiry and officer authority before calling apply().
 */
public final class RaceStartClock {
    private long offsetMs;
    private long uncertaintyMs=Long.MAX_VALUE;
    private long lastSyncElapsedMs;
    private long startElapsedMs=Long.MIN_VALUE;
    private long revision=-1;
    private String epoch="";
    private String commandId="";
    private boolean fired;
    private boolean abandoned;

    public synchronized void updateClock(long authoritativeUtcMs, long requestSentElapsedMs,
                                         long responseReceivedElapsedMs) {
        if(responseReceivedElapsedMs<requestSentElapsedMs) return;
        long rtt=responseReceivedElapsedMs-requestSentElapsedMs;
        if(rtt>5000) return;
        long midpoint=requestSentElapsedMs+rtt/2;
        long candidateOffset=authoritativeUtcMs-midpoint;
        long candidateUncertainty=rtt/2+25;
        if(candidateUncertainty<uncertaintyMs || elapsed()-lastSyncElapsedMs>30000) {
            offsetMs=candidateOffset;
            uncertaintyMs=candidateUncertainty;
            lastSyncElapsedMs=responseReceivedElapsedMs;
        }
    }
    private static long elapsed(){return SystemClock.elapsedRealtime();}
    public synchronized boolean apply(String raceEpoch,long newRevision,String id,
                                      String action,long startUtcMs) {
        if(raceEpoch==null||raceEpoch.isEmpty()||id==null||id.isEmpty())return false;
        if(raceEpoch.equals(epoch)&&newRevision<=revision)return false;
        if(!raceEpoch.equals(epoch)&&revision>=0)return false; // explicit reset for new race
        if(!("start".equals(action)||"new_start".equals(action)||"postpone".equals(action)||
             "abandon".equals(action)||"recall".equals(action)))return false;
        epoch=raceEpoch;revision=newRevision;commandId=id;fired=false;
        abandoned="abandon".equals(action)||"recall".equals(action);
        if(abandoned||"postpone".equals(action))startElapsedMs=Long.MIN_VALUE;
        else startElapsedMs=startUtcMs-offsetMs;
        return true;
    }
    public synchronized long remainingMs(){
        if(startElapsedMs==Long.MIN_VALUE)return Long.MAX_VALUE;
        return startElapsedMs-elapsed();
    }
    public synchronized boolean consumeGun(){
        if(fired||abandoned||startElapsedMs==Long.MIN_VALUE||uncertaintyMs>2000)return false;
        long late=elapsed()-startElapsedMs;
        if(late<0)return false;
        fired=true;
        return late<=1000; // never fire a significantly late gun
    }
    public synchronized long uncertaintyMs(){
        if(uncertaintyMs==Long.MAX_VALUE)return uncertaintyMs;
        return uncertaintyMs+Math.max(0,elapsed()-lastSyncElapsedMs)/1000; // conservative drift allowance
    }
    public synchronized long revision(){return revision;}
    public synchronized String commandId(){return commandId;}
    public synchronized boolean isScheduled(){return startElapsedMs!=Long.MIN_VALUE;}
    public synchronized void resetForNewRace(){revision=-1;epoch="";commandId="";startElapsedMs=Long.MIN_VALUE;fired=false;abandoned=false;}
}
