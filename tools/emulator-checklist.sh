#!/usr/bin/env bash
# Runs the first-launch checklist (app/integration_test/app_test.dart) on a
# connected Android device or emulator through `flutter drive`, which
# writes app/screenshots/*.png and app/build/integration_response_data.json
# via app/test_driver/integration_test.dart. Keeps the device log beside
# them and exits with the test's status.
#
# One script, invoked as one command, because reactivecircus/android-
# emulator-runner runs each line of its `script` in a separate shell: a
# `cd` or a variable set on one line is gone on the next (first run,
# 2026-09-15: `flutter drive` ran from the repo root, found no target, and
# the job still passed).
#
#   bash tools/emulator-checklist.sh [device]     # default emulator-5554
set -uo pipefail
cd "$(dirname "$0")/../app"
device="${1:-emulator-5554}"

status=0
flutter drive --driver=test_driver/integration_test.dart \
  --target=integration_test/app_test.dart -d "$device" || status=$?

mkdir -p build
adb -s "$device" logcat -d -v time > build/logcat.txt || true
echo "flutter drive exit status: $status"
exit "$status"
