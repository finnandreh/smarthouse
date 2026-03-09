#!/usr/bin/env bash
set -euo pipefail

ROOT="/mnt/c/smarthouse"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${SMARTHOUSE_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"

pruned_count=$(docker compose -f "${ROOT}/docker-compose.yml" exec -T postgres psql -U smarthouse -d smarthouse -t -A -c "WITH deleted AS (DELETE FROM revoked_tokens WHERE expires_at < NOW() RETURNING 1) SELECT COUNT(*) FROM deleted;")
remaining_count=$(docker compose -f "${ROOT}/docker-compose.yml" exec -T postgres psql -U smarthouse -d smarthouse -t -A -c "SELECT COUNT(*) FROM revoked_tokens;")

echo "PRUNED_REVOKED_TOKENS=${pruned_count}"
echo "REMAINING_REVOKED_TOKENS=${remaining_count}"
