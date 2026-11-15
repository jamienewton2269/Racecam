#!/bin/sh
# Install loopback pairing service; does not change MediaMTX, DNS, or firewall.
set -eu
[ "$(id -u)" -eq 0 ] || { echo "Run as root" >&2; exit 1; }
BASE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
[ -f "$BASE/receiver.py" ] || exit 1
command -v python3 >/dev/null
if ! id racecam >/dev/null 2>&1; then useradd --system --home-dir /var/lib/racecam --shell /usr/sbin/nologin racecam; fi
install -d -o root -g root -m 0755 /opt/racecam
install -o root -g root -m 0644 "$BASE/receiver.py" /opt/racecam/receiver.py
install -d -o racecam -g racecam -m 0700 /var/lib/racecam
install -d -o root -g root -m 0700 /etc/racecam
if [ ! -e /etc/racecam/receiver.env ]; then
 token=$(python3 -c 'import secrets;print(secrets.token_urlsafe(48))')
 umask 077
 printf 'RACECAM_HOST=127.0.0.1\nRACECAM_PORT=8787\nRACECAM_DB=/var/lib/racecam/racecam.sqlite3\nRACECAM_ADMIN_TOKEN=%s\nRACECAM_CLUB=RaceCam Test Receiver\n' "$token" > /etc/racecam/receiver.env
 chmod 0600 /etc/racecam/receiver.env
fi
cat > /etc/systemd/system/racecam-pairing.service <<'UNIT'
[Unit]
Description=RaceCam loopback pairing service (test)
After=network.target
[Service]
Type=simple
User=racecam
Group=racecam
EnvironmentFile=/etc/racecam/receiver.env
ExecStart=/usr/bin/python3 /opt/racecam/receiver.py
WorkingDirectory=/var/lib/racecam
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/var/lib/racecam
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now racecam-pairing.service
sleep 1
systemctl is-active --quiet racecam-pairing.service
python3 - <<'PY'
from urllib.request import urlopen
import json
v=json.load(urlopen('http://127.0.0.1:8787/health',timeout=3))
assert v['status']=='ready',v
print('Loopback pairing service health PASS')
PY
echo 'MediaMTX remains unchanged.'
