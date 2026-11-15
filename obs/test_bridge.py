#!/usr/bin/env python3
"""Offline OBS bridge contract checks; no running receiver or OBS required."""
import json,threading,urllib.request,urllib.error
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bridge

class FakeStatus(BaseHTTPRequestHandler):
 def do_GET(self):
  body=json.dumps({"generated_ms":1000,"positions":[{"camera_id":"test-cam","race_id":"r1","fix_ms":1000,"latitude":53.48,"longitude":-3.06,"accuracy_m":5,"sog_mps":2.0,"cog_deg":90,"stale":False,"secret":"must-not-leak"}]}).encode()
  self.send_response(200);self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
 def log_message(self,*args):pass

def get(base,path):
 with urllib.request.urlopen(base+path,timeout=3) as r:return r.status,r.headers,r.read()
def main():
 upstream=ThreadingHTTPServer(("127.0.0.1",0),FakeStatus)
 bridge.POSITIONS="http://127.0.0.1:"+str(upstream.server_port)+"/api/race/positions"
 server=ThreadingHTTPServer(("127.0.0.1",0),bridge.Handler)
 threads=[threading.Thread(target=s.serve_forever,daemon=True) for s in (upstream,server)]
 for t in threads:t.start()
 base="http://127.0.0.1:"+str(server.server_port)
 try:
  for path,needle in (("/obs/water",b"On-water yacht positions"),("/obs/handicap",b"Handicap-adjusted race positions")):
   code,headers,body=get(base,path)
   assert code==200 and needle in body,(path,code)
  code,headers,body=get(base,"/obs/api/water")
  data=json.loads(body)
  assert code==200 and len(data["positions"])==1 and data["positions"][0]["latitude"]==53.48
  assert b"must-not-leak" not in body and b"secret" not in body
  assert headers["Cache-Control"]=="no-store"
  code,headers,body=get(base,"/obs/api/handicap")
  assert code==200 and json.loads(body)["approved"] is False
  code,headers,body=get(base,"/health")
  assert code==200 and json.loads(body)["status"]=="ready"
  try:get(base,"/admin/pairings")
  except urllib.error.HTTPError as e:assert e.code==404
  else:raise AssertionError("unexpected admin exposure")
  print("PASS: two OBS displays, water proxy, secret filtering, handicap fail-closed, health, admin isolation")
 finally:
  server.shutdown();upstream.shutdown();server.server_close();upstream.server_close()
if __name__=="__main__":main()
