package org.sailinguk.racecam;

import android.location.Location;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.SystemClock;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.Locale;
import java.util.UUID;
import org.json.JSONObject;

/**
 * Transport-only RaceCam GNSS sender. Feed from the app's existing location listener.
 * Does not request location permission or start a background service.
 * The owning Activity/foreground service controls location consent and lifecycle.
 */
public final class RaceCamTelemetrySender implements AutoCloseable {
    public interface Listener { void onResult(boolean accepted, int httpStatus); }
    private final HandlerThread worker = new HandlerThread("RaceCam-GNSS");
    private final Handler queue;
    private final String endpoint, cameraId, secret, sessionId;
    private final Listener listener;
    private long sequence = 0;
    private long lastFixElapsed = -1;
    private volatile boolean closed = false;

    public RaceCamTelemetrySender(String httpsBaseUrl, String cameraId, String secret, Listener listener) {
        if (httpsBaseUrl == null || !httpsBaseUrl.startsWith("https://"))
            throw new IllegalArgumentException("HTTPS required");
        if (cameraId == null || cameraId.isEmpty() || secret == null || secret.isEmpty())
            throw new IllegalArgumentException("Paired camera credentials required");
        this.endpoint = httpsBaseUrl.replaceAll("/+$", "") + "/api/telemetry";
        this.cameraId = cameraId;
        this.secret = secret;
        this.sessionId = UUID.randomUUID().toString();
        this.listener = listener;
        worker.start();
        queue = new Handler(worker.getLooper());
    }

    /** Call from the existing GNSS location callback. Never call from the UI thread. */
    public void submit(Location fix, String raceId, Integer batteryPct, String cameraStatus) {
        if (closed || fix == null || !fix.hasAccuracy() || fix.getAccuracy() < 0) return;
        final Location snapshot = new Location(fix);
        if (snapshot.getTime() <= 0 || snapshot.getLatitude() < -90 || snapshot.getLatitude() > 90
                || snapshot.getLongitude() < -180 || snapshot.getLongitude() > 180) return;
        // Keep a small, bounded queue by discarding new fixes while a request is in flight.
        // This favours current live positions over backlog accumulation.
        synchronized (this) {
            long elapsed = snapshot.getElapsedRealtimeNanos() / 1000000L;
            if (elapsed > 0 && lastFixElapsed >= 0 && elapsed - lastFixElapsed < 1000) return;
            lastFixElapsed = elapsed;
        }
        final String race = raceId, status = cameraStatus;
        final Integer battery = batteryPct;
        queue.removeCallbacksAndMessages(null);
        final long seq = ++sequence;
        queue.post(() -> transmit(snapshot, race, battery, status, seq));
    }

    private void transmit(Location fix, String race, Integer battery, String status, long seq) {
        if (closed) return;
        HttpURLConnection connection = null;
        int response = -1;
        try {
            JSONObject body = new JSONObject();
            body.put("camera_id", cameraId);
            body.put("session_id", sessionId);
            body.put("sequence", seq);
            body.put("fix_ms", fix.getTime());
            body.put("latitude", fix.getLatitude());
            body.put("longitude", fix.getLongitude());
            body.put("accuracy_m", fix.getAccuracy());
            if (fix.hasSpeed()) body.put("sog_mps", fix.getSpeed());
            if (fix.hasBearing()) body.put("cog_deg", fix.getBearing());
            if (race != null) body.put("race_id", race);
            if (battery != null) body.put("battery_pct", battery);
            if (status != null) body.put("camera_status", status);
            byte[] bytes = body.toString().getBytes(StandardCharsets.UTF_8);
            connection = (HttpURLConnection) new URL(endpoint).openConnection();
            connection.setRequestMethod("POST");
            connection.setConnectTimeout(4000);
            connection.setReadTimeout(4000);
            connection.setRequestProperty("Content-Type", "application/json");
            connection.setRequestProperty("X-RaceCam-Secret", secret);
            connection.setDoOutput(true);
            connection.setFixedLengthStreamingMode(bytes.length);
            try (OutputStream stream = connection.getOutputStream()) { stream.write(bytes); }
            response = connection.getResponseCode();
        } catch (Exception ignored) {
            // Network errors are reported without leaking credentials into logs.
        } finally {
            if (connection != null) connection.disconnect();
        }
        if (listener != null) listener.onResult(response == 202, response);
    }

    @Override public void close() {
        closed = true;
        queue.removeCallbacksAndMessages(null);
        worker.quitSafely();
    }
}
