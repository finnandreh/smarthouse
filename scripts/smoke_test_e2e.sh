#!/usr/bin/env bash
set -euo pipefail

cd /mnt/c/smarthouse
PROVISIONING_MASTER_KEY="${PROVISIONING_MASTER_KEY:-changeme-provisioning-local-dev}"
MQTT_TLS_PORT="${MQTT_TLS_PORT:-8883}"
MQTT_TLS_CA_CERT="${MQTT_TLS_CA_CERT:-/mosquitto/config/certs/ca.crt}"
MQTT_TLS_CLIENT_CERT="${MQTT_TLS_CLIENT_CERT:-/mosquitto/config/certs/test-client.crt}"
MQTT_TLS_CLIENT_KEY="${MQTT_TLS_CLIENT_KEY:-/mosquitto/config/certs/test-client.key}"

token=$(PROVISIONING_MASTER_KEY="${PROVISIONING_MASTER_KEY}" scripts/auth_token.sh smoke-e2e operator home01 device:register 30)

# 1) Ensure stack is up
if ! docker compose ps --status running >/dev/null 2>&1; then
  docker compose up -d --build
fi

# 2) Register sample device
curl -fsS -X POST "http://localhost:8081/devices/register" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${token}" \
  -d '{"id":"device123","house":"home01","type":"relay_module","protocol":"wifi","capabilities":["relay_output","power_monitor"]}' \
  >/tmp/smarthouse_register.json

# 3) Subscribe to one control message in background
rm -f /tmp/smarthouse_control_msg.txt
(
  docker exec smarthouse-mqtt sh -lc "timeout 10 mosquitto_sub --cafile ${MQTT_TLS_CA_CERT} --cert ${MQTT_TLS_CLIENT_CERT} --key ${MQTT_TLS_CLIENT_KEY} -p ${MQTT_TLS_PORT} -h localhost -t platform/home01/device123/control -C 1" \
    >/tmp/smarthouse_control_msg.txt
) &
sub_pid=$!

sleep 1

# 4) Publish motion event trigger
docker exec smarthouse-mqtt sh -lc "mosquitto_pub --cafile ${MQTT_TLS_CA_CERT} --cert ${MQTT_TLS_CLIENT_CERT} --key ${MQTT_TLS_CLIENT_KEY} -p ${MQTT_TLS_PORT} -h localhost -t platform/home01/device123/event -m '{\"event\":\"motion_detected\",\"value\":true}'"

# 5) Wait for subscriber to complete
wait "$sub_pid"

# 6) Print outputs
echo "REGISTER_RESPONSE:"
cat /tmp/smarthouse_register.json
echo

echo "CONTROL_MESSAGE:"
cat /tmp/smarthouse_control_msg.txt
echo
