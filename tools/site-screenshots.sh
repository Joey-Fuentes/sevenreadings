#!/usr/bin/env bash
# Puts the latest checklist screenshots on the site (docs/plan.md, T4):
# downloads every screenshots-<target> artifact of the newest successful
# screenshots.yml run into <site>/screenshots/<target>/ and writes the
# contact sheet, <site>/screenshots/index.html. Needs gh with actions:read.
#
# No successful run in the artifacts' 30-day retention: skips with a note,
# the site still deploys. A run found but nothing downloaded: fails, because
# an empty page that looks finished is the bug (2026-09-16, the first
# deploy: a wrong `gh` call, swallowed, published a page with no targets).
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
# One call, every screenshots-* artifact, each into its own directory.
gh run download "$run" -p 'screenshots-*' -D "$out"
for dir in "$out"/screenshots-*; do
  [ -d "$dir" ] || continue
  mv "$dir" "$out/${dir##*/screenshots-}"
done
rm -f "$out"/*/build/logcat.txt
count=$(ls -d "$out"/*/ 2>/dev/null | wc -l)
echo "screenshots from run $run: $count targets"
if [ "$count" -eq 0 ]; then
  echo "run $run has no screenshots-* artifacts, or the download failed"
  exit 1
fi
python3 "$(dirname "$0")/screenshots-page.py" "$out" "$run"
