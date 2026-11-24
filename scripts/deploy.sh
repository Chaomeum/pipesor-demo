#!/usr/bin/env bash
# Starts orders-api on the runner with the given settings and verifies it through its health check.
set -euo pipefail

settings="${1:?usage: scripts/deploy.sh <settings.env>}"
set -a
# shellcheck source=/dev/null
. "$settings"
set +a
: "${SERVICE_NAME:?}" "${SERVICE_PORT:?}" "${HEALTHCHECK_URL:?}" "${HEALTHCHECK_RETRIES:=3}"

log="${RUNNER_TEMP:-/tmp}/${SERVICE_NAME}.log"
echo "Deploying ${SERVICE_NAME} (commit ${GITHUB_SHA:-local}) with settings from ${settings}"
echo "Effective settings:"
grep -E '^[A-Z_]+=' "$settings" | sed 's/^/  /'
python3 -u app/server.py --name "$SERVICE_NAME" --port "$SERVICE_PORT" > "$log" 2>&1 &
server=$!
trap 'kill "$server" 2>/dev/null || true' EXIT
sleep 2
echo "Service log:"
sed 's/^/  /' "$log"

echo "Verifying deployment: GET ${HEALTHCHECK_URL}"
for attempt in $(seq 1 "$HEALTHCHECK_RETRIES"); do
  if curl -sS --fail --max-time 5 -o /dev/null "$HEALTHCHECK_URL"; then
    echo "Health check passed on attempt ${attempt}: ${SERVICE_NAME} is UP"
    exit 0
  fi
  echo "health check attempt ${attempt}/${HEALTHCHECK_RETRIES} failed"
  sleep 2
done

echo "Error: post-deployment verification could not reach ${SERVICE_NAME} at ${HEALTHCHECK_URL}"
exit 1
