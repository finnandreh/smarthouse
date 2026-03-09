#!/usr/bin/env bash
set -euo pipefail

PROVISIONING_MASTER_KEY="${PROVISIONING_MASTER_KEY:-changeme-provisioning-local-dev}"
SUBJECT="${1:-smoke-client}"
ROLE="${2:-operator}"
HOUSE="${3:-home01}"
SCOPES="${4:-device:register}"
EXPIRES_MINUTES="${5:-30}"

scopes_json="[]"
if [[ -n "${SCOPES}" ]]; then
  IFS=',' read -r -a scope_items <<<"${SCOPES}"
  scopes_json="["
  for item in "${scope_items[@]}"; do
    scopes_json+="\"${item}\","
  done
  scopes_json="${scopes_json%,}]"
fi

payload=$(cat <<JSON
{"subject":"${SUBJECT}","role":"${ROLE}","house":"${HOUSE}","scopes":${scopes_json},"expires_minutes":${EXPIRES_MINUTES}}
JSON
)

curl -fsS -X POST "http://localhost:8081/auth/token" \
  -H "Content-Type: application/json" \
  -H "x-provisioning-key: ${PROVISIONING_MASTER_KEY}" \
  -d "${payload}" | sed -n 's/.*"access_token"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p'
