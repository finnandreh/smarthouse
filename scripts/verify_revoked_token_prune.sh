#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${SMARTHOUSE_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"

before_count=$(docker compose -f "${ROOT}/docker-compose.yml" exec -T postgres psql -U smarthouse -d smarthouse -t -A -c "SELECT COUNT(*) FROM revoked_tokens;")

docker compose -f "${ROOT}/docker-compose.yml" exec -T postgres psql -U smarthouse -d smarthouse -c "INSERT INTO revoked_tokens (jti, subject, expires_at) VALUES ('expired-prune-test', 'verify-prune', NOW() - INTERVAL '1 hour') ON CONFLICT (jti) DO UPDATE SET expires_at = EXCLUDED.expires_at;" >/dev/null

"${ROOT}/scripts/prune_revoked_tokens.sh" >/tmp/prune_revoked_tokens_output.txt

after_count=$(docker compose -f "${ROOT}/docker-compose.yml" exec -T postgres psql -U smarthouse -d smarthouse -t -A -c "SELECT COUNT(*) FROM revoked_tokens;")
exists_expired=$(docker compose -f "${ROOT}/docker-compose.yml" exec -T postgres psql -U smarthouse -d smarthouse -t -A -c "SELECT COUNT(*) FROM revoked_tokens WHERE jti = 'expired-prune-test';")

echo "REVOKED_BEFORE_COUNT=${before_count}"
echo "REVOKED_AFTER_COUNT=${after_count}"
echo "EXPIRED_TEST_ENTRY_EXISTS=${exists_expired}"
echo "PRUNE_SCRIPT_OUTPUT=$(tr '\n' ' ' < /tmp/prune_revoked_tokens_output.txt)"
