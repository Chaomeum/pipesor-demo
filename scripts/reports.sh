#!/usr/bin/env bash
# Starts orders-reports on the runner and waits for its startup probe within the configured deadline.
set -euo pipefail

settings="${1:?usage: scripts/reports.sh <settings.env>}"
set -a
# shellcheck source=/dev/null
. "$settings"
set +a
: "${SERVICE_NAME:?}" "${SERVICE_PORT:?}" "${STARTUP_TIMEOUT_SECONDS:?}"

log="${RUNNER_TEMP:-/tmp}/${SERVICE_NAME}.log"
echo "Deploying ${SERVICE_NAME} (commit ${GITHUB_SHA:-local}) with settings from ${settings}"
echo "Effective settings:"
grep -E '^[A-Z_]+=' "$settings" | sed 's/^/  /'
python3 -u app/server.py --name "$SERVICE_NAME" --port "$SERVICE_PORT" --warmup 8 > "$log" 2>&1 &
server=$!
trap 'kill "$server" 2>/dev/null || true' EXIT

start=$SECONDS
status=000
while [ $((SECONDS - start)) -lt "$STARTUP_TIMEOUT_SECONDS" ]; do
  sleep 1
  status=$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 "http://localhost:${SERVICE_PORT}/health" || true)
  if [ "$status" = 200 ]; then
    echo "Startup probe passed after $((SECONDS - start))s: ${SERVICE_NAME} is ready"
    exit 0
  fi
  echo "startup probe: HTTP ${status} after $((SECONDS - start))s"
done

kill "$server" 2>/dev/null || true
wait "$server" 2>/dev/null || true
echo "Service log:"
grep -v '"GET /health' "$log" | sed 's/^/  /'
echo "Error: ${SERVICE_NAME} was not ready within the ${STARTUP_TIMEOUT_SECONDS}s startup deadline (last probe HTTP ${status})"
exit 1
