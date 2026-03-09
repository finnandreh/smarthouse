#!/usr/bin/env bash
set -euo pipefail

CERT_DIR="/mnt/c/smarthouse/certs"
CONF="${CERT_DIR}/openssl-ca.cnf"
SKIP_RESTART="${SKIP_RESTART:-false}"
SERVICES=(
  "device-registry"
  "automation-engine"
  "bridge-modbus"
  "bridge-knx"
  "bridge-bacnet"
)

if [ ! -f "${CONF}" ]; then
  echo "CA config not found. Run scripts/generate_mqtt_tls_certs.sh first."
  exit 1
fi

for name in "${SERVICES[@]}"; do
  if [ -f "${CERT_DIR}/${name}.crt" ]; then
    openssl ca -config "${CONF}" -revoke "${CERT_DIR}/${name}.crt" || true
  fi

  openssl genrsa -out "${CERT_DIR}/${name}.key" 2048
  openssl req -new -key "${CERT_DIR}/${name}.key" -out "${CERT_DIR}/${name}.csr" -subj "/CN=${name}"
  openssl ca -batch -config "${CONF}" -extensions client_ext -in "${CERT_DIR}/${name}.csr" -out "${CERT_DIR}/${name}.crt"
  chmod 600 "${CERT_DIR}/${name}.key"
  chmod 644 "${CERT_DIR}/${name}.crt"
done

openssl ca -gencrl -config "${CONF}" -out "${CERT_DIR}/ca.crl"

if [ "${SKIP_RESTART}" != "true" ]; then
  docker compose -f /mnt/c/smarthouse/docker-compose.yml restart mqtt device-registry automation-engine bridge-modbus bridge-knx bridge-bacnet
fi

echo "Rotated service certificates and restarted dependent services"
