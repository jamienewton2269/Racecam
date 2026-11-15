package uk.org.sailing.signal;
import android.app.*;import android.content.*;import android.content.pm.ServiceInfo;import android.location.*;import android.net.*;import android.os.*;import android.telephony.*;import java.io.*;import java.text.*;import java.util.*;
public class SurveyService extends Service {
 Handler h=new Handler(Looper.getMainLooper()); LocationManager lm;LocationListener listener;Location last;File csv;long count;boolean running;
 public void onCreate(){super.onCreate();NotificationChannel ch=new NotificationChannel("survey","Signal survey",NotificationManager.IMPORTANCE_LOW);getSystemService(NotificationManager.class).createNotificationChannel(ch);}
 public int onStartCommand(Intent intent,int flags,int id){if(intent!=null&&"STOP".equals(intent.getAction())){stopSelf();return START_NOT_STICKY;}if(running)return START_STICKY;
 Notification n=new Notification.Builder(this,"survey").setContentTitle("Sailing-UK Signal Logger").setContentText("Survey recording every 5 seconds").setSmallIcon(android.R.drawable.ic_menu_mylocation).setContentIntent(PendingIntent.getActivity(this,0,new Intent(this,MainActivity.class),PendingIntent.FLAG_IMMUTABLE)).build();
 if(Build.VERSION.SDK_INT>=29)startForeground(1001,n,ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION);else startForeground(1001,n);
 lm=(LocationManager)getSystemService(LOCATION_SERVICE);listener=l->last=l;
 try{if(lm.isProviderEnabled(LocationManager.GPS_PROVIDER))lm.requestLocationUpdates(LocationManager.GPS_PROVIDER,5000,0,listener);if(lm.isProviderEnabled(LocationManager.NETWORK_PROVIDER))lm.requestLocationUpdates(LocationManager.NETWORK_PROVIDER,5000,0,listener);Location a=lm.getLastKnownLocation(LocationManager.NETWORK_PROVIDER);if(a!=null)last=a;}catch(SecurityException e){stopSelf();return START_NOT_STICKY;}
 File dir=getExternalFilesDir(null);if(dir==null){stopSelf();return START_NOT_STICKY;}csv=new File(dir,"sailing-survey-"+System.currentTimeMillis()+".csv");
 try(FileWriter w=new FileWriter(csv)){w.write("utc,latitude,longitude,accuracy_m,speed_mps,location_age_s,transport,radio,rsrp_dbm,rsrq_db,sinr_db\n");}catch(IOException e){stopSelf();return START_NOT_STICKY;}
 running=true;h.post(tick);return START_STICKY;
 }
 String val(int x){return x==Integer.MAX_VALUE?"":Integer.toString(x);}
 Runnable tick=new Runnable(){public void run(){if(!running)return;String transport="unknown",radio="unavailable",rsrp="",rsrq="",sinr="";try{ConnectivityManager cm=(ConnectivityManager)getSystemService(CONNECTIVITY_SERVICE);Network active=cm.getActiveNetwork();NetworkCapabilities cap=cm.getNetworkCapabilities(active);if(cap!=null)transport=cap.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR)?"cellular":cap.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)?"wifi":"other";TelephonyManager tm=(TelephonyManager)getSystemService(TELEPHONY_SERVICE);List<CellInfo> cells=tm.getAllCellInfo();if(cells!=null)for(CellInfo c:cells){if(!c.isRegistered())continue;if(c instanceof CellInfoNr){CellSignalStrengthNr s=(CellSignalStrengthNr)c.getCellSignalStrength();radio="5G NR";rsrp=val(s.getSsRsrp());rsrq=val(s.getSsRsrq());sinr=val(s.getSsSinr());break;}if(c instanceof CellInfoLte){CellSignalStrengthLte s=((CellInfoLte)c).getCellSignalStrength();radio="4G LTE";rsrp=val(s.getRsrp());rsrq=val(s.getRsrq());sinr=val(s.getRssnr());break;}radio=c.getClass().getSimpleName();}}catch(Exception ignored){}
 Location l=last;double age=l==null?-1:(SystemClock.elapsedRealtimeNanos()-l.getElapsedRealtimeNanos())/1e9;boolean fresh=l!=null&&age>=0&&age<=60;
 SimpleDateFormat fmt=new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'",Locale.US);fmt.setTimeZone(TimeZone.getTimeZone("UTC"));String row=String.join(",",fmt.format(new Date()),fresh?""+l.getLatitude():"",fresh?""+l.getLongitude():"",fresh?""+l.getAccuracy():"",fresh?""+l.getSpeed():"",fresh?String.format(Locale.US,"%.1f",age):"",transport,radio,rsrp,rsrq,sinr)+"\n";
 try(FileWriter w=new FileWriter(csv,true)){w.write(row);count++;}catch(IOException ignored){}h.postDelayed(this,5000);
 }};
 public void onDestroy(){running=false;h.removeCallbacks(tick);if(lm!=null&&listener!=null)try{lm.removeUpdates(listener);}catch(Exception ignored){}super.onDestroy();}
 public IBinder onBind(Intent i){return null;}
}