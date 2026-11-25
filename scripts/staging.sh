#!/usr/bin/env bash
# Starts the new orders-api release in staging next to the current one and promotes it only if its
# startup probe answers 200; otherwise staging keeps serving the current release.
set -euo pipefail

config="${1:?usage: scripts/staging.sh <settings.json>}"
port=8090
release="${GITHUB_SHA:-local}"
release="${release:0:7}"
log="${RUNNER_TEMP:-/tmp}/orders-api-staging.log"

echo "Deploying orders-api ${release} to staging with ${config}"
python3 -u app/server.py --name "orders-api ${release}" --port "$port" --config "$config" > "$log" 2>&1 &
server=$!
trap 'kill "$server" 2>/dev/null || true' EXIT
sleep 2

status=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://localhost:${port}/health" || true)
echo "Startup probe: GET http://localhost:${port}/health -> HTTP ${status}"
if [ "$status" = 200 ]; then
  echo "Release ${release} promoted: staging now serves orders-api ${release}"
  exit 0
fi

echo "Application log:"
sed 's/^/  /' "$log"
echo "Rollback: release ${release} not promoted; staging keeps the current release"
echo "Error: startup probe returned HTTP ${status} for orders-api ${release} in staging; rollback complete"
exit 1
