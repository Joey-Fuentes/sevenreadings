#!/usr/bin/env bash
# Runs the first-launch checklist (app/integration_test/app_test.dart) on a
# device through `flutter drive`, which writes app/screenshots/*.png and
# app/build/integration_response_data.json via
# app/test_driver/integration_test.dart, then checks that the run produced
# what it should. Exits non-zero if the test failed, or if fewer than nine
# screenshots or either launch timing came out of it: a job that passes
# having run nothing is a bug (2026-09-15, the first run).
#
#   bash tools/checklist.sh emulator-5554                       # Android
#   xvfb-run -a -s "-screen 0 1280x800x24" bash tools/checklist.sh linux
#
# One script, invoked as one command, because reactivecircus/android-
# emulator-runner runs each line of its `script` in a separate shell: a
# `cd` or a variable set on one line is gone on the next.
set -uo pipefail
cd "$(dirname "$0")/../app"
device="${1:-emulator-5554}"
rm -rf screenshots
mkdir -p build

status=0
flutter drive --driver=test_driver/integration_test.dart \
  --target=integration_test/app_test.dart -d "$device" || status=$?

case "$device" in
  emulator-*) adb -s "$device" logcat -d -v time > build/logcat.txt || true ;;
esac
echo "flutter drive exit status: $status"

n=$(ls screenshots/*.png 2>/dev/null | wc -l)
echo "screenshots: $n"
report=build/integration_response_data.json
if [ -f "$report" ]; then cat "$report"; else echo "no report written"; fi
if [ "$status" -ne 0 ]; then exit "$status"; fi
[ "$n" -eq 9 ] || { echo "expected 9 screenshots, found $n"; exit 1; }
jq -e '.first_launch_ms and .second_launch_ms' "$report" > /dev/null \
  || { echo "launch timings missing from $report"; exit 1; }
