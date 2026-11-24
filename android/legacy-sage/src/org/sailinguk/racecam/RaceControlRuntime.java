package org.sailinguk.racecam;
import android.content.SharedPreferences;
import android.os.Handler;
import android.os.Looper;
import android.widget.TextView;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/** Foreground countdown monitor. No official audio until integration tests pass. */
public final class RaceControlRuntime implements AutoCloseable {
    private final RaceStartClock clock=new RaceStartClock();
    private final ScheduledExecutorService executor=Executors.newSingleThreadScheduledExecutor();
    private final Handler ui=new Handler(Looper.getMainLooper());
    private final TextView status;
    private volatile boolean closed;
    private RaceMqttCommands commands;
    private final Runnable display=new Runnable(){public void run(){
        if(closed)return;
        long uncertainty=clock.uncertaintyMs();
        if(!clock.isClockReady()||uncertainty>2000)status.setText("Race timing: waiting for trusted clock");
        else if(commands==null||!commands.isConnected())status.setText("Race timing: MQTT offline; start not confirmed");
        else if(!clock.isScheduled())status.setText("Race timing: synchronised; awaiting start");
        else {long remaining=clock.remainingMs();status.setText(remaining>0?
            "Race start in "+((remaining+999)/1000)+" s | uncertainty "+uncertainty+" ms":
            "Scheduled start reached (monitor only)");}
        ui.postDelayed(this,100);
    }};
    public RaceControlRuntime(SharedPreferences p,TextView status)throws Exception{
        this.status=status;
        String endpoint=required(p,"clock_url");
        RaceControlVerifier verifier=new RaceControlVerifier(required(p,"race_signing_key"),required(p,"club_id"),required(p,"race_id"),required(p,"race_epoch"));
        commands=new RaceMqttCommands(required(p,"mqtt_host"),p.getInt("mqtt_port",8883),required(p,"mqtt_user"),required(p,"mqtt_password"),required(p,"command_topic"),required(p,"ack_topic"),new RaceCommandController(clock,verifier));
        executor.scheduleWithFixedDelay(()->{
            if(closed)return;
            try{RaceClockSync.sample(endpoint,clock);if(!closed&&clock.isClockReady())commands.start();}
            catch(Exception e){android.util.Log.w("RaceCam","Clock sample failed",e);}
        },0,5,TimeUnit.SECONDS);
        ui.post(display);
    }
    private static String required(SharedPreferences p,String key){String value=p.getString(key,"");if(value.isEmpty())throw new IllegalArgumentException("Missing "+key);return value;}
    public void close(){closed=true;ui.removeCallbacks(display);executor.shutdownNow();if(commands!=null)commands.close();}
}
