package org.sailinguk.racecam;

import android.content.Context;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.SystemClock;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import javax.net.ssl.SSLSocket;
import javax.net.ssl.SSLSocketFactory;
import javax.net.ssl.SSLParameters;

/**
 * Independent GPS/MQTT 5 transport. No camera dependency.
 * Credentials and endpoint are supplied by the app's private preferences after pairing.
 * QoS 1 is acknowledged before a fix is considered delivered.
 */
public final class RaceCamMqttTelemetry implements LocationListener {
    public interface Status { void onStatus(String message); }
    private final Context context;
    private final Status status;
    private final HandlerThread worker = new HandlerThread("racecam-gps-mqtt");
    private Handler handler;
    private LocationManager locations;
    private volatile boolean active;
    private long sequence;
    private final String session = UUID.randomUUID().toString();
    private int packetId = 1;
    private String pendingFix;
    private boolean flushScheduled;
    private SSLSocket socket;
    private InputStream input;
    private OutputStream output;
    private String host, username, password, topic, device;
    private int port;

    public RaceCamMqttTelemetry(Context context, Status status) {
        this.context=context.getApplicationContext(); this.status=status;
    }
    public void start(String brokerHost, int brokerPort, String user, String secret,
                      String publishTopic, String deviceId) {
        if(active) return;
        if(brokerHost==null || brokerHost.isEmpty() || brokerPort<1 || brokerPort>65535 ||
           publishTopic==null || publishTopic.isEmpty() || deviceId==null || deviceId.isEmpty() ||
           user==null || secret==null || secret.isEmpty()) {
            status.onStatus("MQTT not paired"); return;
        }
        host=brokerHost;port=brokerPort;username=user;password=secret;topic=publishTopic;device=deviceId;
        active=true;worker.start();handler=new Handler(worker.getLooper());
        locations=(LocationManager)context.getSystemService(Context.LOCATION_SERVICE);
        try {
            locations.requestLocationUpdates(LocationManager.GPS_PROVIDER,1000,0,this,worker.getLooper());
            status.onStatus("GPS waiting for fix");
        } catch(SecurityException e) {status.onStatus("GPS permission required");stop();}
          catch(IllegalArgumentException e) {status.onStatus("GPS provider unavailable");stop();}
    }
    @Override public void onLocationChanged(Location fix) {
        if(!active || fix==null || !fix.hasAccuracy()) return;
        final long seq=++sequence;
        final String json="{\"schema\":1,\"device_id\":\""+jsonEscape(device)+"\",\"session_id\":\""+session+
            "\",\"sequence\":"+seq+",\"fix_ms\":"+fix.getTime()+",\"latitude\":"+fix.getLatitude()+
            ",\"longitude\":"+fix.getLongitude()+",\"accuracy_m\":"+fix.getAccuracy()+
            (fix.hasSpeed()?",\"sog_mps\":"+fix.getSpeed():"")+
            (fix.hasBearing()?",\"cog_deg\":"+fix.getBearing():"")+"}";
        handler.post(()->{pendingFix=json;if(!flushScheduled){flushScheduled=true;handler.post(this::flushLatest);}});
    }
    private void flushLatest() {
        flushScheduled=false;
        String next=pendingFix;pendingFix=null;
        if(next!=null)publish(next);
        if(pendingFix!=null && !flushScheduled){flushScheduled=true;handler.post(this::flushLatest);}
    }
    private static String jsonEscape(String s) {return s.replace("\\","\\\\").replace("\"","\\\"");}
    private void publish(String json) {
        if(!active) return;
        try {
            if(socket==null) connect();
            int id=packetId++;if(packetId>65535)packetId=1;
            ByteArrayOutputStream body=new ByteArrayOutputStream();
            utf(body,topic);body.write(id>>8);body.write(id&255);body.write(0); // MQTT 5 properties length
            body.write(json.getBytes(StandardCharsets.UTF_8));
            packet(0x32,body.toByteArray()); // PUBLISH QoS 1
            int header=input.read();if(header!=0x40)throw new IOException("Expected PUBACK");
            int length=readVar(input);byte[] ack=new byte[length];readFully(input,ack);
            if(length<2 || ((ack[0]&255)<<8 | (ack[1]&255))!=id ||
               (length>2 && (ack[2]&255)>=0x80))throw new IOException("PUBACK rejected");
            status.onStatus("GPS sent (MQTT QoS 1)");
        } catch(Exception e) {close();status.onStatus("MQTT disconnected: "+e.getMessage());}
    }
    private void connect() throws IOException {
        SSLSocket s=(SSLSocket)SSLSocketFactory.getDefault().createSocket(host,port);
        SSLParameters params=s.getSSLParameters();params.setEndpointIdentificationAlgorithm("HTTPS");s.setSSLParameters(params);
        s.setSoTimeout(10000);s.startHandshake();socket=s;input=s.getInputStream();output=s.getOutputStream();
        ByteArrayOutputStream b=new ByteArrayOutputStream();
        utf(b,"MQTT");b.write(5);b.write(0xC2);b.write(0);b.write(0);b.write(0); // MQTT5, user+pass, clean start, keepalive disabled, props
        utf(b,"racecam-"+session.substring(0,8));utf(b,username);utf(b,password);
        packet(0x10,b.toByteArray());
        if(input.read()!=0x20)throw new IOException("Expected CONNACK");
        int length=readVar(input);byte[] ack=new byte[length];readFully(input,ack);
        if(length<3 || ack[1]!=0)throw new IOException("Broker refused connection");
    }
    private void packet(int header,byte[] body) throws IOException {
        output.write(header);var(output,body.length);output.write(body);output.flush();
    }
    private static void utf(OutputStream out,String s) throws IOException {
        byte[] b=s.getBytes(StandardCharsets.UTF_8);
        if(b.length>65535)throw new IOException("MQTT string too long");
        out.write(b.length>>8);out.write(b.length&255);out.write(b);
    }
    private static void var(OutputStream out,int n)throws IOException {
        do {int digit=n%128;n/=128;if(n>0)digit|=128;out.write(digit);}while(n>0);
    }
    private static int readVar(InputStream in)throws IOException {
        int value=0,multiplier=1;
        for(int i=0;i<4;i++){int d=in.read();if(d<0)throw new EOFException();value+=(d&127)*multiplier;
            if((d&128)==0)return value;multiplier*=128;}
        throw new IOException("Invalid MQTT length");
    }
    private static void readFully(InputStream in,byte[] b)throws IOException {
        int pos=0;while(pos<b.length){int n=in.read(b,pos,b.length-pos);if(n<0)throw new EOFException();pos+=n;}
    }
    private void close(){try{if(socket!=null)socket.close();}catch(Exception ignored){}socket=null;}
    @Override public void onProviderEnabled(String p){}
    @Override public void onProviderDisabled(String p){status.onStatus("GPS disabled");}
    @Override public void onStatusChanged(String p,int s,Bundle b){}
    public void stop(){active=false;if(locations!=null)locations.removeUpdates(this);
        if(handler!=null)handler.post(this::close);}
}
