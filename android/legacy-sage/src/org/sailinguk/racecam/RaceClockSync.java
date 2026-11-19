package org.sailinguk.racecam;

import android.os.SystemClock;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.URL;
import javax.net.ssl.HttpsURLConnection;

/**
 * Samples an authenticated HTTPS clock endpoint for RaceStartClock.
 * Endpoint JSON: {"utc_ms": 1790000000000}; timestamp taken immediately
 * before sending the response. Call on a background thread only.
 * HTTPS validates the server certificate and hostname.
 */
public final class RaceClockSync {
    private RaceClockSync() {}
    public static long sample(String endpoint, RaceStartClock clock) throws Exception {
        URL url=new URL(endpoint);
        if(!"https".equalsIgnoreCase(url.getProtocol()))
            throw new SecurityException("Clock endpoint requires HTTPS");
        HttpsURLConnection connection=(HttpsURLConnection)url.openConnection();
        connection.setConnectTimeout(3000);
        connection.setReadTimeout(3000);
        connection.setUseCaches(false);
        connection.setRequestProperty("Accept","application/json");
        long sent=SystemClock.elapsedRealtime();
        try {
            if(connection.getResponseCode()!=200)
                throw new java.io.IOException("Clock HTTP "+connection.getResponseCode());
            ByteArrayOutputStream bytes=new ByteArrayOutputStream();
            try(InputStream stream=connection.getInputStream()) {
                byte[] buffer=new byte[256];int n;
                while((n=stream.read(buffer))!=-1) {
                    if(bytes.size()+n>2048)throw new java.io.IOException("Clock response too large");
                    bytes.write(buffer,0,n);
                }
            }
            long received=SystemClock.elapsedRealtime();
            long utc=new JSONObject(bytes.toString("UTF-8")).getLong("utc_ms");
            if(utc<=0)throw new java.io.IOException("Invalid clock timestamp");
            clock.updateClock(utc,sent,received);
            return received-sent;
        } finally {connection.disconnect();}
    }
}
