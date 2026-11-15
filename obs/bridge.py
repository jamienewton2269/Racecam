#!/usr/bin/env python3
"""Local-only OBS development bridge. NOT an Internet-facing API."""
import json,os,urllib.request,urllib.error
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parent
HOST="127.0.0.1"
PORT=int(os.getenv("RACECAM_OBS_PORT","8790"))
POSITIONS=os.getenv("RACECAM_POSITIONS_URL","http://127.0.0.1:8789/api/race/positions")
# Do not accept arbitrary upstream URLs from HTTP clients.
class Handler(BaseHTTPRequestHandler):
 def send_bytes(self,code,body,mime):
  self.send_response(code)
  self.send_header("Content-Type",mime)
  self.send_header("Cache-Control","no-store")
  self.send_header("X-Content-Type-Options","nosniff")
  self.send_header("Content-Security-Policy","default-src 'self'; connect-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; object-src 'none'; frame-ancestors 'self'")
  self.send_header("Content-Length",str(len(body)))
  self.end_headers();self.wfile.write(body)
 def do_GET(self):
  path=self.path.split("?",1)[0]
  if path in ("/obs/water","/obs/handicap"):
   filename="water.html" if path=="/obs/water" else "handicap.html"
   return self.send_bytes(200,(ROOT/filename).read_bytes(),"text/html; charset=utf-8")
  if path=="/obs/api/water":
   try:
    with urllib.request.urlopen(POSITIONS,timeout=3) as r:
     data=json.load(r)
    if not isinstance(data,dict) or not isinstance(data.get("positions"),list):raise ValueError("Invalid status response")
    # Return only fields needed for the on-water display; camera ID is a pseudonymous identifier.
    fields=("camera_id","race_id","fix_ms","latitude","longitude","accuracy_m","sog_mps","cog_deg","stale")
    clean=[{k:p[k] for k in fields if k in p} for p in data["positions"] if isinstance(p,dict)]
    body=json.dumps({"generated_ms":data.get("generated_ms"),"positions":clean},separators=(",",":")).encode()
    return self.send_bytes(200,body,"application/json")
   except (OSError,ValueError,urllib.error.URLError):
    return self.send_bytes(503,b'{"error":"receiver_unavailable"}',"application/json")
  if path=="/obs/api/handicap":
   # Fail closed until RaceDay Manager's signed/approved snapshot integration exists.
   return self.send_bytes(200,b'{"approved":false,"standings":[]}',"application/json")
  if path=="/health":
   return self.send_bytes(200,b'{"status":"ready","scope":"loopback-only"}',"application/json")
  return self.send_bytes(404,b'{"error":"not_found"}',"application/json")
if __name__=="__main__":
 print("OBS development bridge listening on 127.0.0.1:"+str(PORT),flush=True)
 ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
