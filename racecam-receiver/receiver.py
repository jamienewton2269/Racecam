#!/usr/bin/env python3
"""RaceCam loopback pairing service. No external listeners."""
import hashlib,hmac,json,os,secrets,sqlite3,time,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse
DB=os.environ.get("RACECAM_DB","/var/lib/racecam/racecam.sqlite3")
HOST=os.environ.get("RACECAM_HOST","127.0.0.1")
PORT=int(os.environ.get("RACECAM_PORT","8787"))
PUBLIC=os.environ.get("RACECAM_PUBLIC_URL","").rstrip("/")
SRT_PORT=int(os.environ.get("RACECAM_SRT_PORT","8890"))
ADMIN=os.environ.get("RACECAM_ADMIN_TOKEN","")
CLUB=os.environ.get("RACECAM_CLUB","Sailing Club")
LOCK=threading.Lock()
ATTEMPTS={}
def db():
 c=sqlite3.connect(DB,timeout=10)
 c.execute("PRAGMA journal_mode=WAL")
 c.execute("CREATE TABLE IF NOT EXISTS sessions (digest TEXT PRIMARY KEY, expires INTEGER NOT NULL, used INTEGER NOT NULL DEFAULT 0)")
 c.execute("CREATE TABLE IF NOT EXISTS cameras (id TEXT PRIMARY KEY, secret TEXT NOT NULL, created INTEGER NOT NULL, revoked INTEGER NOT NULL DEFAULT 0)")
 c.commit()
 return c
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def hash_secret(s):
 salt=secrets.token_bytes(16)
 return "pbkdf2_sha256$210000$"+salt.hex()+"$"+hashlib.pbkdf2_hmac("sha256",s.encode(),salt,210000).hex()
def check_secret(stored,supplied):
 if not isinstance(supplied,str) or len(supplied)>256:return False
 try:
  alg,n,salt,hashval=stored.split("$")
  return alg=="pbkdf2_sha256" and int(n)==210000 and hmac.compare_digest(hashlib.pbkdf2_hmac("sha256",supplied.encode(),bytes.fromhex(salt),210000),bytes.fromhex(hashval))
 except (ValueError,AttributeError):return False
def limited(ip):
 now=time.monotonic()
 with LOCK:
  for key,values in list(ATTEMPTS.items()):
   values[:]=[x for x in values if now-x<60]
   if not values:del ATTEMPTS[key]
  values=ATTEMPTS.setdefault(ip,[])
  if len(values)>=15:return True
  values.append(now)
  return False
class Handler(BaseHTTPRequestHandler):
 def reply(self,status,obj):
  raw=json.dumps(obj,separators=(",",":")).encode()
  self.send_response(status)
  self.send_header("Content-Type","application/json")
  self.send_header("Content-Length",str(len(raw)))
  self.send_header("Cache-Control","no-store")
  self.end_headers()
  self.wfile.write(raw)
 def read_json(self):
  try:
   n=int(self.headers.get("Content-Length","0"))
   return json.loads(self.rfile.read(n)) if 0<n<=4096 else None
  except (ValueError,UnicodeError,TypeError):return None
 def authorized(self):
  return bool(ADMIN) and hmac.compare_digest(self.headers.get("Authorization",""),"Bearer "+ADMIN)
 def do_GET(self):
  return self.reply(200,{"service":"racecam-pairing","status":"ready"}) if urlparse(self.path).path=="/health" else self.reply(404,{"error":"not_found"})
 def do_POST(self):
  path=urlparse(self.path).path
  if path=="/api/mediamtx/auth":
   if self.client_address[0] not in ("127.0.0.1","::1"):return self.reply(403,{"error":"local_only"})
   data=self.read_json()
   if not isinstance(data,dict):return self.reply(400,{"error":"invalid_request"})
   if data.get("action")!="publish" or data.get("protocol")!="srt":return self.reply(403,{"error":"denied"})
   cam,pw,stream=data.get("user"),data.get("password"),data.get("path")
   if not all(isinstance(x,str) for x in (cam,pw,stream)) or stream!=cam:return self.reply(403,{"error":"denied"})
   with db() as c:row=c.execute("SELECT secret,revoked FROM cameras WHERE id=?",(cam,)).fetchone()
   return self.reply(200,{"authorized":True}) if row and not row[1] and check_secret(row[0],pw) else self.reply(403,{"error":"denied"})
  if path=="/admin/pairings":
   if self.client_address[0] not in ("127.0.0.1","::1") or not self.authorized():return self.reply(403,{"error":"forbidden"})
   if not PUBLIC.startswith("https://") or not urlparse(PUBLIC).hostname:return self.reply(503,{"error":"configure_https_public_url"})
   token=secrets.token_urlsafe(32);expiry=int(time.time())+300
   with db() as c:
    c.execute("DELETE FROM sessions WHERE expires < ?",(int(time.time()),))
    c.execute("INSERT INTO sessions(digest,expires) VALUES (?,?)",(digest(token),expiry))
   payload={"version":1,"type":"racecam-receiver-pair","club":CLUB,"pair_url":PUBLIC+"/api/pair","token":token,"expires":expiry}
   return self.reply(201,{"payload":payload,"qr_text":json.dumps(payload,separators=(",",":")),"expires":expiry})
  if path=="/admin/cameras/revoke":
   if self.client_address[0] not in ("127.0.0.1","::1") or not self.authorized():return self.reply(403,{"error":"forbidden"})
   data=self.read_json()
   if not isinstance(data,dict) or not isinstance(data.get("camera_id"),str):return self.reply(400,{"error":"invalid_request"})
   with db() as c:cur=c.execute("UPDATE cameras SET revoked=1 WHERE id=?",(data["camera_id"],))
   return self.reply(200 if cur.rowcount else 404,{"revoked":bool(cur.rowcount)})
  if path=="/api/pair":
   if limited(self.client_address[0]):return self.reply(429,{"error":"rate_limited"})
   data=self.read_json()
   if not isinstance(data,dict) or not isinstance(data.get("token"),str) or len(data["token"])>256:return self.reply(400,{"error":"invalid_json"})
   now=int(time.time());cam="cam-"+secrets.token_hex(6);secret=secrets.token_urlsafe(32)
   with db() as c:
    c.execute("BEGIN IMMEDIATE")
    cur=c.execute("UPDATE sessions SET used=1 WHERE digest=? AND used=0 AND expires>=?",(digest(data["token"]),now))
    if cur.rowcount!=1:return self.reply(403,{"error":"invalid_expired_or_used_token"})
    c.execute("INSERT INTO cameras(id,secret,created) VALUES (?,?,?)",(cam,hash_secret(secret),now))
   return self.reply(201,{"version":1,"club":CLUB,"camera_id":cam,"srt":{"host":urlparse(PUBLIC).hostname,"port":SRT_PORT,"stream_id":"publish:"+cam+":"+cam+":"+secret},"credential":secret,"warning":"Verify MediaMTX auth before production"})
  return self.reply(404,{"error":"not_found"})
if __name__=="__main__":
 if not ADMIN:raise SystemExit("Set RACECAM_ADMIN_TOKEN")
 db().close()
 print("RaceCam loopback pairing service listening",flush=True)
 ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
