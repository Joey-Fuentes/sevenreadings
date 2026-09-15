#!/usr/bin/env bash
# Puts the latest checklist screenshots on the site (docs/plan.md, T4):
# downloads every screenshots-<target> artifact of the newest successful
# screenshots.yml run into <site>/screenshots/<target>/ and writes the
# contact sheet, <site>/screenshots/index.html. Needs gh with actions:read.
# Skips, with a note, when no run has succeeded in the last 30 days (the
# artifacts' retention), so the site still deploys.
#
#   bash tools/site-screenshots.sh app/build/web
set -uo pipefail
site="${1:?site directory}"
run=$(gh run list --workflow=screenshots.yml --status success --limit 1 \
  --json databaseId --jq '.[0].databaseId' 2>/dev/null || true)
if [ -z "$run" ]; then
  echo "no successful screenshots run to publish"
  exit 0
fi
out="$site/screenshots"
rm -rf "$out" && mkdir -p "$out"
names=$(gh run view "$run" --json artifacts --jq '.artifacts[].name' | grep '^screenshots-' || true)
for name in $names; do
  target="${name#screenshots-}"
  gh run download "$run" -n "$name" -D "$out/$target" || { echo "download of $name failed"; continue; }
  rm -f "$out/$target/build/logcat.txt"
done
python3 "$(dirname "$0")/screenshots-page.py" "$out" "$run"
