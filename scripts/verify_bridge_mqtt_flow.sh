#!/usr/bin/env bash
set -euo pipefail

MQTT_TLS_PORT="${MQTT_TLS_PORT:-8883}"
MQTT_TLS_CA_CERT="${MQTT_TLS_CA_CERT:-/mosquitto/config/certs/ca.crt}"
MQTT_TLS_CLIENT_CERT="${MQTT_TLS_CLIENT_CERT:-/mosquitto/config/certs/test-client.crt}"
MQTT_TLS_CLIENT_KEY="${MQTT_TLS_CLIENT_KEY:-/mosquitto/config/certs/test-client.key}"

rm -f /tmp/bridge_msg.txt
(
  docker exec smarthouse-mqtt sh -lc "timeout 10 mosquitto_sub --cafile ${MQTT_TLS_CA_CERT} --cert ${MQTT_TLS_CLIENT_CERT} --key ${MQTT_TLS_CLIENT_KEY} -p ${MQTT_TLS_PORT} -h localhost -t platform/home01/bridge-modbus-01/event -C 1" >/tmp/bridge_msg.txt
) &
sub_pid=$!

sleep 1
curl -fsS -X POST http://localhost:8091/emit-test -H "Content-Type: application/json" -d '{"event":"register_read","value":230.1}' >/tmp/bridge_emit.json
wait "$sub_pid"

if [[ ! -s /tmp/bridge_msg.txt ]]; then
  echo "Bridge MQTT verification failed: no event payload captured"
  exit 1
fi

echo "BRIDGE_EMIT_RESPONSE=$(cat /tmp/bridge_emit.json)"
echo "BRIDGE_MQTT_MESSAGE=$(cat /tmp/bridge_msg.txt)"
