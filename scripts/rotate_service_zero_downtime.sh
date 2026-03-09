#!/usr/bin/env bash
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 <service-name>"
  echo "Supported: device-registry automation-engine bridge-modbus bridge-knx bridge-bacnet"
  exit 1
fi

SERVICE="$1"
ROOT="/mnt/c/smarthouse"
CERT_DIR="${ROOT}/certs"
OVERLAP_DIR="${CERT_DIR}/overlap/${SERVICE}"
STAMP="$(date +%Y%m%d-%H%M%S)"
NEXT_PREFIX="${SERVICE}-next-${STAMP}"
CURRENT_CRT="${CERT_DIR}/${SERVICE}.crt"
CURRENT_KEY="${CERT_DIR}/${SERVICE}.key"

mkdir -p "${OVERLAP_DIR}"

if [ ! -f "${CURRENT_CRT}" ] || [ ! -f "${CURRENT_KEY}" ]; then
  echo "Missing current cert/key for ${SERVICE}"
  exit 1
fi

cp "${CURRENT_CRT}" "${OVERLAP_DIR}/${STAMP}.prev.crt"
cp "${CURRENT_KEY}" "${OVERLAP_DIR}/${STAMP}.prev.key"

# Keep CN unchanged for overlap rollout so existing ACL identity remains valid.
"${ROOT}/scripts/issue_client_cert.sh" "${SERVICE}" --cn "${SERVICE}" --out-prefix "${NEXT_PREFIX}"

cp "${CERT_DIR}/${NEXT_PREFIX}.crt" "${CURRENT_CRT}"
cp "${CERT_DIR}/${NEXT_PREFIX}.key" "${CURRENT_KEY}"

# Restart only target service to pick up new cert. Broker and other services stay up.
docker compose -f "${ROOT}/docker-compose.yml" restart "${SERVICE}" >/tmp/rotate_${SERVICE}.log 2>&1
sleep 2

case "${SERVICE}" in
  device-registry)
    HEALTH_URL="http://localhost:8081/health"
    ;;
  automation-engine)
    HEALTH_URL="http://localhost:8082/health"
    ;;
  bridge-modbus)
    HEALTH_URL="http://localhost:8091/health"
    ;;
  bridge-knx)
    HEALTH_URL="http://localhost:8092/health"
    ;;
  bridge-bacnet)
    HEALTH_URL="http://localhost:8093/health"
    ;;
  *)
    echo "Unsupported service: ${SERVICE}"
    exit 1
    ;;
esac

if ! curl -fsS "${HEALTH_URL}" >/dev/null; then
  echo "HEALTH_CHECK_FAILED=rolling_back"
  cp "${OVERLAP_DIR}/${STAMP}.prev.crt" "${CURRENT_CRT}"
  cp "${OVERLAP_DIR}/${STAMP}.prev.key" "${CURRENT_KEY}"
  docker compose -f "${ROOT}/docker-compose.yml" restart "${SERVICE}" >/tmp/rotate_${SERVICE}_rollback.log 2>&1
  echo "ROLLED_BACK=true"
  exit 1
fi

echo "ZERO_DOWNTIME_ROTATE=success"
echo "SERVICE=${SERVICE}"
echo "NEW_CERT_PREFIX=${NEXT_PREFIX}"
echo "PREV_CERT=${OVERLAP_DIR}/${STAMP}.prev.crt"
echo "To finalize and revoke old cert: scripts/finalize_zero_downtime_rotation.sh ${SERVICE} ${OVERLAP_DIR}/${STAMP}.prev.crt"
