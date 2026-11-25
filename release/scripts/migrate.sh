#!/usr/bin/env bash
# Applies the release's database migrations (a stand-in: no database exists).
set -euo pipefail
for migration in 001_create_orders 002_add_order_status 003_add_paid_total_index; do
  echo "  applied ${migration} on ${MIGRATION_TARGET:-orders-db}"
done
