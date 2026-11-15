#!/usr/bin/env python3
"""Temporary GPS fix integration test for status API, with guaranteed cleanup."""
import sqlite3,secrets,time,json,urllib.request,os
from receiver import hash_secret
DB=os.getenv("RACECAM_DB","/var/lib/racecam/racecam.sqlite3")
cam="status-test-"+secrets.token_hex(5); session=secrets.token_hex(8); now=int(time.time()*1000)
secret=secrets.token_urlsafe(32)
c=sqlite3.connect(DB,timeout=10)
try:
 c.execute("INSERT INTO cameras(id,secret,created,revoked) VALUES (?,?,?,0)",(cam,hash_secret(secret),now//1000))
 c.commit()
 payload=dict(camera_id=cam,session_id=session,sequence=1,fix_ms=now,latitude=53.48,longitude=-3.06,accuracy_m=3.5,sog_mps=2.0,cog_deg=90.0,race_id="integration")
 req=urllib.request.Request("http://127.0.0.1:8788/api/telemetry",json.dumps(payload).encode(),{"Content-Type":"application/json","X-RaceCam-Secret":secret})
 assert urllib.request.urlopen(req,timeout=5).status==202
 data=json.load(urllib.request.urlopen("http://127.0.0.1:8789/api/race/positions",timeout=5))
 rows=[p for p in data["positions"] if p["camera_id"]==cam]
 assert len(rows)==1 and rows[0]["race_id"]=="integration" and not rows[0]["stale"],rows
 c.execute("UPDATE cameras SET revoked=1 WHERE id=?",(cam,));c.commit()
 data=json.load(urllib.request.urlopen("http://127.0.0.1:8789/api/race/positions",timeout=5))
 assert all(p["camera_id"]!=cam for p in data["positions"])
 print("PASS: authenticated GPS ingest -> live positions feed -> revoked camera hidden")
finally:
 c.execute("DELETE FROM telemetry WHERE camera_id=?",(cam,))
 c.execute("DELETE FROM telemetry_cursor WHERE camera_id=?",(cam,))
 c.execute("DELETE FROM cameras WHERE id=?",(cam,))
 c.commit();c.close()
