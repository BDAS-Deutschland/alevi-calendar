#!/bin/sh
# Daily job: scrape + build, then upload dist/ if a deploy target is set in config.json.
# Manual data lives in data/overrides.json, which this job only reads.
set -eu
cd "$(dirname "$0")/.."
mkdir -p logs
exec >>logs/update.log 2>&1
exec 9>logs/.lock
flock -n 9 || { echo "$(date -Is) already running"; exit 0; }

echo "=== $(date -Is)"
python3 scripts/build.py

TARGET=$(python3 -c 'import json;print(json.load(open("config.json")).get("deploy_target") or "")')
if [ -n "$TARGET" ]; then
  # --delete removes files on the server that no longer exist in dist/ (e.g. a dropped event)
  rsync -rlz --delete --chmod=D755,F644 dist/ "$TARGET"
  echo "deployed to $TARGET"
else
  echo "no deploy_target in config.json, skipped upload"
fi
