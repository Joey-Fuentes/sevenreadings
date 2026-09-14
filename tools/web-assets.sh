#!/usr/bin/env bash
# Fetches sqlite3.wasm (matching the sqlite3 package in the lockfile) and
# compiles the drift worker. Both land in app/web/ and are gitignored.
set -euo pipefail
cd "$(dirname "$0")/.."

sqlite3_version=$(awk '/^  sqlite3:$/{f=1} f && /version:/{gsub(/"/,"",$2); print $2; exit}' pubspec.lock)
[ -n "$sqlite3_version" ] || { echo "sqlite3 not in pubspec.lock; run flutter pub get" >&2; exit 1; }

# Release tags in simolus3/sqlite3.dart are "sqlite3-<version>". Verify if this 404s.
url="https://github.com/simolus3/sqlite3.dart/releases/download/sqlite3-${sqlite3_version}/sqlite3.wasm"
echo "sqlite3 ${sqlite3_version}: ${url}"
curl -fsSL --retry 3 -o app/web/sqlite3.wasm "$url"

(cd app && dart compile js -O4 -o web/drift_worker.js web/worker.dart)
ls -la app/web/sqlite3.wasm app/web/drift_worker.js
