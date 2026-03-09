#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${SMARTHOUSE_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
ENV_FILE="${1:-${ROOT}/.env}"
ENV_EXAMPLE="${ROOT}/.env.example"

if [ ! -f "${ENV_FILE}" ]; then
  if [ -f "${ENV_EXAMPLE}" ]; then
    cp "${ENV_EXAMPLE}" "${ENV_FILE}"
  else
    touch "${ENV_FILE}"
  fi
fi

BACKUP_FILE="${ENV_FILE}.bak.$(date +%Y%m%d%H%M%S)"
cp "${ENV_FILE}" "${BACKUP_FILE}"

generate_token() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 24
  else
    date +%s%N | sha256sum | awk '{print $1}' | cut -c1-48
  fi
}

EDGE_API_KEY_ADMIN_NEW="edge-admin-$(generate_token)"
EDGE_API_KEY_OPERATOR_NEW="edge-operator-$(generate_token)"

update_env_var() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}=" "${ENV_FILE}"; then
    sed -i "s|^${key}=.*$|${key}=${value}|" "${ENV_FILE}"
  else
    echo "${key}=${value}" >>"${ENV_FILE}"
  fi
}

update_env_var "EDGE_API_KEY" "${EDGE_API_KEY_ADMIN_NEW}"
update_env_var "EDGE_API_KEY_ADMIN" "${EDGE_API_KEY_ADMIN_NEW}"
update_env_var "EDGE_API_KEY_OPERATOR" "${EDGE_API_KEY_OPERATOR_NEW}"

echo "EDGE_API_KEY_ROTATION=completed"
echo "ENV_FILE=${ENV_FILE}"
echo "BACKUP_FILE=${BACKUP_FILE}"
echo "EDGE_API_KEY_ADMIN_NEW=${EDGE_API_KEY_ADMIN_NEW}"
echo "EDGE_API_KEY_OPERATOR_NEW=${EDGE_API_KEY_OPERATOR_NEW}"
echo "NEXT_STEP=docker compose up -d --force-recreate edge-controller"
