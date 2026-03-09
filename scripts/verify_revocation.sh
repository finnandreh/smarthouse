#!/usr/bin/env bash
set -euo pipefail

CERT_DIR="/mnt/c/smarthouse/certs"
MQTT_TLS_PORT="${MQTT_TLS_PORT:-8883}"
MQTT_TLS_CA_CERT="${MQTT_TLS_CA_CERT:-/mosquitto/config/certs/ca.crt}"

# Issue a dedicated cert for revocation test.
/mnt/c/smarthouse/scripts/issue_client_cert.sh revocation-test

# Connection should work before revocation.
if docker exec smarthouse-mqtt sh -lc "mosquitto_pub --cafile ${MQTT_TLS_CA_CERT} --cert /mosquitto/config/certs/revocation-test.crt --key /mosquitto/config/certs/revocation-test.key -p ${MQTT_TLS_PORT} -h localhost -t platform/revocation/pre -m '{\"event\":\"pre_revoke\"}'" >/tmp/revoke_pre.log 2>&1; then
  echo "REVOCATION_PRECHECK=success"
else
  echo "REVOCATION_PRECHECK=failure"
  exit 1
fi

# Revoke cert and reload broker by restart.
/mnt/c/smarthouse/scripts/revoke_client_cert.sh revocation-test
docker compose -f /mnt/c/smarthouse/docker-compose.yml restart mqtt >/tmp/revoke_restart.log 2>&1
sleep 2

# Connection must fail after revocation.
if docker exec smarthouse-mqtt sh -lc "mosquitto_pub --cafile ${MQTT_TLS_CA_CERT} --cert /mosquitto/config/certs/revocation-test.crt --key /mosquitto/config/certs/revocation-test.key -p ${MQTT_TLS_PORT} -h localhost -t platform/revocation/post -m '{\"event\":\"post_revoke\"}'" >/tmp/revoke_post.log 2>&1; then
  echo "REVOCATION_UNEXPECTED=revoked_cert_still_works"
  exit 1
else
  echo "REVOCATION_EXPECTED=revoked_cert_blocked"
fi
