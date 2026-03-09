#!/usr/bin/env bash
set -euo pipefail

ROOT="/mnt/c/smarthouse"
LOG_TEXT="$(docker compose -f "${ROOT}/docker-compose.yml" logs mqtt --no-color --tail=500)"

count_protocol="$(printf '%s' "$LOG_TEXT" | grep -c 'Protocol error' || true)"
count_unknown_ca="$(printf '%s' "$LOG_TEXT" | grep -c 'unknown ca' || true)"
count_no_cert="$(printf '%s' "$LOG_TEXT" | grep -c 'did not return a certificate' || true)"

echo "MQTT_SECURITY_PROTOCOL_ERRORS=${count_protocol}"
echo "MQTT_SECURITY_UNKNOWN_CA=${count_unknown_ca}"
echo "MQTT_SECURITY_NO_CERT=${count_no_cert}"
