#!/usr/bin/env bash
# Launches the installed Flatpak on a fresh sandbox and proves it starts:
# the content database appears in the sandbox's data directory (the
# first-launch copy ran, so assets, path_provider and the writable home all
# work inside the sandbox), a window titled Seven Readings exists, and an
# X-level screenshot of it is kept. Writes app/screenshots/flatpak-genesis-1.png
# and app/build/integration_response_data.json (the copy time), the layout
# the site's screenshots page expects.
#
#   xvfb-run -a -s "-screen 0 1280x800x24" bash tools/flatpak-smoke.sh
set -uo pipefail
app=org.sevenreadings.SevenReadings
cd "$(dirname "$0")/.."
mkdir -p app/screenshots app/build
data="$HOME/.var/app/$app/data"
rm -rf "$data"   # a first launch, every time

start=$(date +%s%3N)
flatpak run "$app" > app/build/flatpak-run.log 2>&1 &
pid=$!
# The app writes the copy as content/content-<version>.sqlite under its
# application-support directory (packages/sr_data, open_native.dart).
db=""
for _ in $(seq 1 180); do
  db=$(find "$data" -name 'content-*.sqlite' 2>/dev/null | head -n1)
  [ -n "$db" ] && break
  kill -0 "$pid" 2>/dev/null || break
  sleep 1
done
copied=$(( $(date +%s%3N) - start ))
sleep 6   # the reader's first frame after the copy
import -window root app/screenshots/flatpak-genesis-1.png || true
window=$(xdotool search --name 'Seven Readings' 2>/dev/null | head -n1 || true)
kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null
echo "--- flatpak run output ---"; cat app/build/flatpak-run.log; echo "---"

status=0
if [ -n "$db" ]; then
  echo "content database in the sandbox after ${copied} ms: $db ($(stat -c %s "$db") bytes)"
else
  echo "FAIL: no content database appeared under $data"; status=1
fi
if [ -n "$window" ]; then
  echo "window titled Seven Readings: id $window"
else
  echo "FAIL: no window titled Seven Readings"; status=1
fi
printf '{"first_launch_ms": %s, "view": "the Flatpak, first launch in the sandbox"}\n' "$copied" \
  > app/build/integration_response_data.json
exit $status
