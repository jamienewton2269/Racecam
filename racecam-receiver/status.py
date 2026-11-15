#!/usr/bin/env python3
"""Loopback-only read API for RaceCam controller and OBS bridge."""
import json,sqlite3,os,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
DB=os.getenv("RACECAM_DB","/var/lib/racecam/racecam.sqlite3")
PORT=int(os.getenv("RACECAM_STATUS_PORT","8789"))
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  if self.path=="/health":data={"service":"racecam-status","status":"ready"}
  elif self.path=="/api/race/positions":
   with sqlite3.connect(DB,timeout=5) as c:
    rows=c.execute("""SELECT t.camera_id,t.race_id,t.fix_ms,t.received_ms,t.latitude,t.longitude,t.accuracy_m,t.sog_mps,t.cog_deg
      FROM telemetry t JOIN cameras c ON c.id=t.camera_id AND c.revoked=0
      WHERE t.rowid=(SELECT t2.rowid FROM telemetry t2 WHERE t2.camera_id=t.camera_id ORDER BY t2.fix_ms DESC,t2.received_ms DESC LIMIT 1)""").fetchall()
   now=int(time.time()*1000)
   data={"generated_ms":now,"positions":[dict(camera_id=r[0],race_id=r[1],fix_ms=r[2],received_ms=r[3],latitude=r[4],longitude=r[5],accuracy_m=r[6],sog_mps=r[7],cog_deg=r[8],age_ms=max(0,now-r[2]),stale=(now-r[2]>15000 or r[6]>50)) for r in rows]}
  else:
   self.send_error(404);return
  raw=json.dumps(data,separators=(",",":")).encode()
  self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Cache-Control","no-store");self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)
if __name__=="__main__":
 ThreadingHTTPServer(("127.0.0.1",PORT),Handler).serve_forever()
