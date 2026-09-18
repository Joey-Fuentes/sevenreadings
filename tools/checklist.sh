#!/usr/bin/env bash
# Runs the first-launch checklist (app/integration_test/app_test.dart) on a
# device through `flutter drive`, which writes app/screenshots/*.png and
# app/build/integration_response_data.json via
# app/test_driver/integration_test.dart, then checks that the run produced
# what it should. Exits non-zero if the test failed, or if fewer than ten
# screenshots (nine for a store build) or either launch timing came out of it: a job that passes
# having run nothing is a bug (2026-09-15, the first run).
#
#   bash tools/checklist.sh emulator-5554                       # Android
#   xvfb-run -a -s "-screen 0 1280x800x24" bash tools/checklist.sh linux
#   "$CHROMEWEBDRIVER/chromedriver" --port=4444 &
#   bash tools/checklist.sh chrome                              # headless web
#   bash tools/checklist.sh windows                             # Git Bash
#   bash tools/checklist.sh macos
#   bash tools/checklist.sh <simulator udid>                    # iOS, booted
#
# Desktop devices render their own screenshots (no integration_test plugin
# there); Android, iOS and web get them from the plugin. Either way the
# driver writes the same files.
#
# One script, invoked as one command, because reactivecircus/android-
# emulator-runner runs each line of its `script` in a separate shell: a
# `cd` or a variable set on one line is gone on the next.
# macOS ships bash 3.2, where "${extra[@]}" on an empty array is an
# "unbound variable" under set -u (fixed in bash 4.4); hence the
# ${extra[@]+...} form below. First macOS run, 2026-09-17.
set -uo pipefail
cd "$(dirname "$0")/../app"
device="${1:-emulator-5554}"
# SR_DISTRIBUTION (env, default direct) is passed to the build; a store
# value hides the Support band and screen, and the test then takes nine
# screenshots instead of ten (the store listings' run).
distribution="${SR_DISTRIBUTION:-direct}"
case "$distribution" in play|appstore|msstore) expected=9 ;; *) expected=10 ;; esac
rm -rf screenshots
mkdir -p build

extra=()
case "$device" in
  # web-server + chromedriver is the headless form that works in CI;
  # `-d chrome` launches its own Chrome and waits forever for a debugger.
  chrome) device=web-server; extra=(--browser-name=chrome --headless --driver-port=4444) ;;
esac
status=0
flutter drive --driver=test_driver/integration_test.dart \
  --target=integration_test/app_test.dart -d "$device" \
  --dart-define=SR_DISTRIBUTION="$distribution" \
  ${extra[@]+"${extra[@]}"} || status=$?

case "$device" in
  emulator-*) adb -s "$device" logcat -d -v time > build/logcat.txt || true ;;
esac
echo "flutter drive exit status: $status"

n=$(ls screenshots/*.png 2>/dev/null | wc -l)
echo "screenshots: $n"
report=build/integration_response_data.json
if [ -f "$report" ]; then cat "$report"; else echo "no report written"; fi
if [ "$status" -ne 0 ]; then exit "$status"; fi
[ "$n" -eq "$expected" ] || { echo "expected $expected screenshots ($distribution build), found $n"; exit 1; }
jq -e '.first_launch_ms and .second_launch_ms' "$report" > /dev/null \
  || { echo "launch timings missing from $report"; exit 1; }
