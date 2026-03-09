#!/usr/bin/env bash
set -euo pipefail

if [ $# -ne 2 ]; then
  echo "Usage: $0 <service-name> <previous-cert-path>"
  exit 1
fi

SERVICE="$1"
PREV_CERT="$2"
ROOT="/mnt/c/smarthouse"

if [ ! -f "${PREV_CERT}" ]; then
  echo "Previous cert not found: ${PREV_CERT}"
  exit 1
fi

"${ROOT}/scripts/revoke_client_cert.sh" --cert "${PREV_CERT}"
docker compose -f "${ROOT}/docker-compose.yml" restart mqtt >/tmp/finalize_revoke_mqtt.log 2>&1
sleep 2

echo "FINALIZE_ROTATION=success"
echo "SERVICE=${SERVICE}"
echo "REVOKED_CERT=${PREV_CERT}"
