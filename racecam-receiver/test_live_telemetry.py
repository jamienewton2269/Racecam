#!/usr/bin/env python3
"""Live receiver integration test; creates and revokes a temporary camera."""
import os,json,time,secrets,sqlite3,urllib.request,urllib.error
base="http://127.0.0.1:8788"
db=os.getenv("RACECAM_DB","/var/lib/racecam/racecam.sqlite3")
def post(path,payload,secret=None):
 headers={"Content-Type":"application/json"}
 if secret:headers["X-RaceCam-Secret"]=secret
 req=urllib.request.Request(base+path,json.dumps(payload).encode(),headers)
 try:
  with urllib.request.urlopen(req,timeout=5) as r:return r.status,json.load(r)
 except urllib.error.HTTPError as e:return e.code,json.load(e)
from receiver import hash_secret
cam="integration-"+secrets.token_hex(6)
secret=secrets.token_urlsafe(32)
session=secrets.token_hex(8)
now=int(time.time()*1000)
fix={"camera_id":cam,"session_id":session,"sequence":1,"fix_ms":now,"latitude":53.5,"longitude":-3.05,"accuracy_m":4.0,"sog_mps":2.2,"cog_deg":135.0,"race_id":"integration-test"}
c=sqlite3.connect(db)
try:
 c.execute("INSERT INTO cameras(id,secret,created,revoked) VALUES (?,?,?,0)",(cam,hash_secret(secret),int(time.time())))
 c.commit()
 assert post("/api/telemetry",fix,"wrong")[0]==403,"bad credential accepted"
 assert post("/api/telemetry",fix,secret)[0]==202,"valid fix rejected"
 assert post("/api/telemetry",fix,secret)[0]==409,"duplicate accepted"
 fix["sequence"]=2
 assert post("/api/telemetry",fix,secret)[0]==202,"next sequence rejected"
 c.execute("UPDATE cameras SET revoked=1 WHERE id=?",(cam,));c.commit()
 fix["sequence"]=3
 assert post("/api/telemetry",fix,secret)[0]==403,"revoked camera accepted"
 print("PASS: invalid secret rejected, valid fixes accepted, duplicate rejected, revocation enforced")
finally:
 c.execute("DELETE FROM telemetry WHERE camera_id=?",(cam,))
 c.execute("DELETE FROM telemetry_cursor WHERE camera_id=?",(cam,))
 c.execute("DELETE FROM cameras WHERE id=?",(cam,))
 c.commit();c.close()
