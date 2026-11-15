#!/bin/sh
# Receiver-side OBS bridge installer. Deliberately leaves MediaMTX and OBS VM untouched.
set -eu
[ "$(id -u)" -eq 0 ] || { echo 'Root required' >&2; exit 1; }
BASE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
for f in bridge.py water.html handicap.html racecam-obs-bridge.service; do
 [ -f "$BASE/$f" ] || { echo "Missing $f" >&2; exit 1; }
done
id racecam >/dev/null 2>&1 || { echo 'Install receiver pairing service first' >&2; exit 1; }
python3 -m py_compile "$BASE/bridge.py"
python3 "$BASE/test_bridge.py"
install -d -o root -g root -m 0755 /opt/racecam/obs
for f in bridge.py water.html handicap.html; do install -o root -g root -m 0644 "$BASE/$f" "/opt/racecam/obs/$f"; done
install -o root -g root -m 0644 "$BASE/racecam-obs-bridge.service" /etc/systemd/system/racecam-obs-bridge.service
systemctl daemon-reload
systemctl enable --now racecam-obs-bridge.service
sleep 1
systemctl is-active --quiet racecam-obs-bridge.service
python3 - <<'PY'
import json,urllib.request
base='http://127.0.0.1:8790'
assert json.load(urllib.request.urlopen(base+'/health',timeout=3))['status']=='ready'
for page in ('water','handicap'):
 assert urllib.request.urlopen(base+'/obs/'+page,timeout=3).status==200
print('PASS: OBS bridge running on receiver loopback 8790')
PY
echo 'OBS VM not configured; authenticated remote transport still required.'
