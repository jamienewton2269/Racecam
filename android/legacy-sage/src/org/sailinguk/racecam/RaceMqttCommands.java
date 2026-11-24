package org.sailinguk.racecam;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import javax.net.ssl.*;

/** Independent MQTT 5 command connection; exact provisioned topics only. */
public final class RaceMqttCommands implements AutoCloseable {
    private final String host,user,password,topic,ackTopic;
    private final int port;
    private final RaceCommandController controller;
    private volatile boolean running;
    private volatile SSLSocket socket;
    private Thread worker;
    private InputStream in;
    private OutputStream out;
    private int nextId=2;
    public RaceMqttCommands(String host,int port,String user,String password,String topic,String ackTopic,RaceCommandController controller){
        if(topic.isEmpty()||ackTopic.isEmpty()||topic.contains("+")||topic.contains("#")||ackTopic.contains("+")||ackTopic.contains("#"))throw new IllegalArgumentException("Exact topics required");
        this.host=host;this.port=port;this.user=user;this.password=password;this.topic=topic;this.ackTopic=ackTopic;this.controller=controller;
    }
    public synchronized void start(){if(worker!=null)return;running=true;worker=new Thread(this::loop,"race-command-mqtt");worker.start();}
    private void loop(){while(running){try{connect();while(running){int h=in.read();if(h<0)throw new EOFException();byte[] b=body();if((h>>4)==3)receive(h,b);else if((h>>4)==14)throw new IOException("Broker disconnected");}}catch(Exception e){disconnect();if(running)try{Thread.sleep(2000);}catch(InterruptedException ignored){}}}}
    private void connect()throws Exception{
        SSLSocket s=(SSLSocket)SSLSocketFactory.getDefault().createSocket();socket=s;
        s.connect(new InetSocketAddress(host,port),5000);s.setSoTimeout(10000);
        SSLParameters p=s.getSSLParameters();p.setEndpointIdentificationAlgorithm("HTTPS");s.setSSLParameters(p);s.startHandshake();
        in=s.getInputStream();out=s.getOutputStream();
        ByteArrayOutputStream b=new ByteArrayOutputStream();utf(b,"MQTT");b.write(5);b.write(0xc2);b.write(0);b.write(0);b.write(0);
        utf(b,"race-control-"+UUID.randomUUID());utf(b,user);utf(b,password);send(0x10,b.toByteArray());
        if(in.read()!=0x20)throw new IOException("CONNACK expected");byte[] a=body();if(a.length<3||a[1]!=0)throw new IOException("Connection rejected");
        b.reset();b.write(0);b.write(1);b.write(0);utf(b,topic);b.write(1);send(0x82,b.toByteArray());
        if(in.read()!=0x90)throw new IOException("SUBACK expected");a=body();ByteArrayInputStream q=new ByteArrayInputStream(a);
        if(q.read()!=0||q.read()!=1)throw new IOException("Wrong SUBACK");skip(q,var(q));int reason=q.read();if(reason<0||reason>1)throw new IOException("Subscription rejected");
        s.setSoTimeout(0);
    }
    private void receive(int h,byte[] b)throws Exception{
        ByteArrayInputStream q=new ByteArrayInputStream(b);int hi=q.read(),lo=q.read();if(hi<0||lo<0)throw new EOFException();
        byte[] name=new byte[(hi<<8)|lo];read(q,name);int qos=(h>>1)&3;int id=0;
        if(qos==1){hi=q.read();lo=q.read();if(hi<0||lo<0)throw new EOFException();id=(hi<<8)|lo;}else if(qos!=0)throw new IOException("Unsupported QoS");
        skip(q,var(q));byte[] payload=new byte[q.available()];read(q,payload);
        if(topic.equals(new String(name,StandardCharsets.UTF_8))){
            try{String ack=controller.receive(new String(payload,StandardCharsets.UTF_8)).toString();
                ByteArrayOutputStream a=new ByteArrayOutputStream();utf(a,ackTopic);int n=nextId++;if(nextId>65535)nextId=2;a.write(n>>8);a.write(n&255);a.write(0);a.write(ack.getBytes(StandardCharsets.UTF_8));send(0x32,a.toByteArray());
            }catch(Exception rejected){android.util.Log.w("RaceCam","Command rejected or acknowledgement failed",rejected);}
        }
        if(qos==1)send(0x40,new byte[]{(byte)(id>>8),(byte)id});
    }
    private byte[] body()throws IOException{int n=var(in);if(n>65536)throw new IOException("Packet too large");byte[] b=new byte[n];read(in,b);return b;}
    private void send(int h,byte[] b)throws IOException{out.write(h);int n=b.length;do{int d=n%128;n/=128;out.write(d|(n>0?128:0));}while(n>0);out.write(b);out.flush();}
    private static int var(InputStream i)throws IOException{int n=0,m=1;for(int k=0;k<4;k++){int d=i.read();if(d<0)throw new EOFException();n+=(d&127)*m;if((d&128)==0)return n;m*=128;}throw new IOException("Invalid length");}
    private static void utf(OutputStream o,String s)throws IOException{byte[] b=s.getBytes(StandardCharsets.UTF_8);if(b.length>65535)throw new IOException("String too long");o.write(b.length>>8);o.write(b.length&255);o.write(b);}
    private static void read(InputStream i,byte[] b)throws IOException{for(int p=0;p<b.length;){int n=i.read(b,p,b.length-p);if(n<0)throw new EOFException();p+=n;}}
    private static void skip(InputStream i,int n)throws IOException{while(n-->0)if(i.read()<0)throw new EOFException();}
    private void disconnect(){try{if(socket!=null)socket.close();}catch(IOException ignored){}}
    public synchronized void close(){running=false;disconnect();if(worker!=null)worker.interrupt();}
}
