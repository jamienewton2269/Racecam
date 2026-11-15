#!/usr/bin/env python3
"""RaceCam GPS ingest, loopback only. Publish /api/telemetry via HTTPS reverse proxy."""
import json,os,sqlite3,time,hmac,hashlib,math,datetime
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Lock
DB=os.getenv("RACECAM_DB","/var/lib/racecam/racecam.sqlite3")
PORT=int(os.getenv("RACECAM_TELEMETRY_PORT","8788"))
LOCK=Lock()
def verify(stored,secret):
 try:
  alg,n,salt,expected=stored.split("$")
  if alg!="pbkdf2_sha256" or int(n)!=210000 or not isinstance(secret,str) or len(secret)>256:return False
  got=hashlib.pbkdf2_hmac("sha256",secret.encode(),bytes.fromhex(salt),210000)
  return hmac.compare_digest(got,bytes.fromhex(expected))
 except (ValueError,TypeError,AttributeError):return False
def connect():
 c=sqlite3.connect(DB,timeout=10)
 c.execute("PRAGMA busy_timeout=10000")
 c.execute("CREATE TABLE IF NOT EXISTS telemetry (camera_id TEXT NOT NULL, session_id TEXT NOT NULL, sequence INTEGER NOT NULL, received_ms INTEGER NOT NULL, fix_ms INTEGER NOT NULL, latitude REAL NOT NULL, longitude REAL NOT NULL, accuracy_m REAL NOT NULL, sog_mps REAL, cog_deg REAL, race_id TEXT, battery_pct INTEGER, camera_status TEXT, PRIMARY KEY(camera_id,session_id,sequence))")
 c.execute("CREATE TABLE IF NOT EXISTS telemetry_cursor (camera_id TEXT NOT NULL, session_id TEXT NOT NULL, sequence INTEGER NOT NULL, PRIMARY KEY(camera_id,session_id))")
 c.commit();return c
def number(x,lo,hi):
 return type(x) in (float,int) and math.isfinite(x) and lo<=x<=hi
class Handler(BaseHTTPRequestHandler):
 def send(self,code,data):
  raw=json.dumps(data,separators=(",",":")).encode()
  self.send_response(code)
  self.send_header("Content-Type","application/json")
  self.send_header("Content-Length",str(len(raw)))
  self.send_header("Cache-Control","no-store")
  self.end_headers();self.wfile.write(raw)
 def do_GET(self):
  if self.path=="/health":return self.send(200,{"service":"racecam-telemetry","status":"ready"})
  return self.send(404,{"error":"not_found"})
 def do_POST(self):
  if self.path!="/api/telemetry":return self.send(404,{"error":"not_found"})
  try:
   length=int(self.headers.get("Content-Length","0"))
   if not 0<length<=2048:return self.send(413,{"error":"size"})
   p=json.loads(self.rfile.read(length))
   if not isinstance(p,dict):raise ValueError()
  except (ValueError,UnicodeError,TypeError):return self.send(400,{"error":"invalid_json"})
  cam=p.get("camera_id");session=p.get("session_id");seq=p.get("sequence")
  if not isinstance(cam,str) or not 1<=len(cam)<=64 or not isinstance(session,str) or not 1<=len(session)<=64 or not session.isascii() or type(seq)!=int or not 0<=seq<2**63:return self.send(400,{"error":"identity"})
  lat=p.get("latitude");lon=p.get("longitude");acc=p.get("accuracy_m");fix=p.get("fix_ms");sog=p.get("sog_mps");cog=p.get("cog_deg")
  if not (number(lat,-90,90) and number(lon,-180,180) and number(acc,0,100000) and type(fix)==int and (sog is None or number(sog,0,200)) and (cog is None or number(cog,0,360))):return self.send(400,{"error":"invalid_fix"})
  now=int(time.time()*1000)
  # Reject wildly future-dated observations; preserve delayed data up to 24h for outage replay.
  if not now-86400000<=fix<=now+30000:return self.send(422,{"error":"timestamp_out_of_range"})
  race=p.get("race_id");status=p.get("camera_status");battery=p.get("battery_pct")
  if race is not None and (not isinstance(race,str) or len(race)>64):return self.send(400,{"error":"race_id"})
  if status is not None and (not isinstance(status,str) or len(status)>32):return self.send(400,{"error":"camera_status"})
  if battery is not None and (type(battery)!=int or not 0<=battery<=100):return self.send(400,{"error":"battery_pct"})
  secret=self.headers.get("X-RaceCam-Secret","")
  try:
   with connect() as c:row=c.execute("SELECT secret,revoked FROM cameras WHERE id=?",(cam,)).fetchone()
  except sqlite3.Error:return self.send(503,{"error":"database_unavailable"})
  if not row or row[1] or not verify(row[0],secret):return self.send(403,{"error":"denied"})
  with LOCK:
   try:
    with connect() as c:
     c.execute("BEGIN IMMEDIATE")
     prev=c.execute("SELECT sequence FROM telemetry_cursor WHERE camera_id=? AND session_id=?",(cam,session)).fetchone()
     if prev and seq<=prev[0]:return self.send(409,{"error":"duplicate_or_old_sequence"})
     c.execute("INSERT INTO telemetry(camera_id,session_id,sequence,received_ms,fix_ms,latitude,longitude,accuracy_m,sog_mps,cog_deg,race_id,battery_pct,camera_status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",(cam,session,seq,now,fix,lat,lon,acc,sog,cog,race,battery,status))
     c.execute("INSERT INTO telemetry_cursor(camera_id,session_id,sequence) VALUES (?,?,?) ON CONFLICT(camera_id,session_id) DO UPDATE SET sequence=excluded.sequence",(cam,session,seq))
   except sqlite3.Error:return self.send(503,{"error":"database_unavailable"})
  return self.send(202,{"accepted":True,"sequence":seq,"received_ms":now})
if __name__=="__main__":
 connect().close()
 ThreadingHTTPServer(("127.0.0.1",PORT),Handler).serve_forever()
