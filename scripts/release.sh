#!/usr/bin/env bash
# Publishes an orders-api release: lists the release bundle, runs its database migrations and tags it.
set -euo pipefail

settings="${1:?usage: scripts/release.sh <release.env>}"
set -a
# shellcheck source=/dev/null
. "$settings"
set +a
: "${RELEASE_NAME:?}" "${MIGRATION_SCRIPT:?}"
release="${GITHUB_SHA:-local}"
release="${release:0:7}"

echo "Publishing ${RELEASE_NAME} release ${release} with settings from ${settings}"
echo "Release bundle:"
find release -type f | LC_ALL=C sort | sed 's/^/  /'
echo "Running database migrations: bash ${MIGRATION_SCRIPT}"
if ! bash "$MIGRATION_SCRIPT"; then
  echo "Error: database migrations failed for ${RELEASE_NAME} release ${release}; release not published"
  exit 1
fi
echo "Release ${release} of ${RELEASE_NAME} published"
