#!/usr/bin/env bash
# Non-destructive synthetic H.264 -> SRT -> MediaMTX -> RTSP smoke test.
# Run on receiver host (or a host with access to its SRT/RTSP ports).
set -euo pipefail
for cmd in ffmpeg ffprobe timeout; do command -v "$cmd" >/dev/null || { echo "Missing: $cmd" >&2; exit 2; }; done
: "${RACECAM_TEST_SRT_URL:?Set full SRT publish URL including the temporary test camera streamid}"
: "${RACECAM_TEST_RTSP_URL:?Set matching RTSP playback URL for that test camera}"
DURATION="${RACECAM_TEST_SECONDS:-12}"
case "$DURATION" in *[!0-9]*|'') echo "RACECAM_TEST_SECONDS must be an integer" >&2; exit 2;; esac
[ "$DURATION" -ge 5 ] && [ "$DURATION" -le 120 ] || { echo "Duration must be 5..120 seconds" >&2; exit 2; }
logdir="$(mktemp -d)"
publisher=""
cleanup() {
  if [ -n "$publisher" ]; then kill "$publisher" 2>/dev/null || true; wait "$publisher" 2>/dev/null || true; fi
  rm -rf "$logdir"
}
trap cleanup EXIT INT TERM
echo "Starting temporary synthetic 720p/25 H.264 publisher (no GPS)."
ffmpeg -hide_banner -nostdin -loglevel error -re -f lavfi -i 'testsrc2=size=1280x720:rate=25' \
  -t "$DURATION" -an -c:v libx264 -preset ultrafast -tune zerolatency \
  -pix_fmt yuv420p -g 50 -f mpegts "$RACECAM_TEST_SRT_URL" >"$logdir/publish.log" 2>&1 &
publisher="$!"
sleep 3
if ! kill -0 "$publisher" 2>/dev/null; then
  echo "FAIL: SRT publisher exited before RTSP probe." >&2
  sed -E 's/(passphrase|password|streamid)=[^& ]+/\1=[REDACTED]/g' "$logdir/publish.log" >&2
  exit 1
fi
echo "Probing MediaMTX RTSP playback..."
if ! timeout 12 ffprobe -v error -rtsp_transport tcp -select_streams v:0 \
  -show_entries stream=codec_name,width,height -of default=noprint_wrappers=1 \
  "$RACECAM_TEST_RTSP_URL" >"$logdir/probe.log" 2>"$logdir/probe.err"; then
  echo "FAIL: RTSP playback unavailable. Check SRT authentication, path and MediaMTX logs." >&2
  exit 1
fi
cat "$logdir/probe.log"
grep -qx 'codec_name=h264' "$logdir/probe.log" || { echo "FAIL: unexpected video codec" >&2; exit 1; }
grep -qx 'width=1280' "$logdir/probe.log" || { echo "FAIL: unexpected width" >&2; exit 1; }
grep -qx 'height=720' "$logdir/probe.log" || { echo "FAIL: unexpected height" >&2; exit 1; }
echo "PASS: synthetic H.264 published via SRT and decoded metadata via RTSP."
echo "NEXT: test camera revocation, reconnect and actual Android A71 video."
