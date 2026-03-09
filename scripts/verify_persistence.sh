#!/usr/bin/env bash
set -euo pipefail

cd /mnt/c/smarthouse
PROVISIONING_MASTER_KEY="${PROVISIONING_MASTER_KEY:-changeme-provisioning-local-dev}"
MQTT_TLS_PORT="${MQTT_TLS_PORT:-8883}"
MQTT_TLS_CA_CERT="${MQTT_TLS_CA_CERT:-/mosquitto/config/certs/ca.crt}"
MQTT_TLS_CLIENT_CERT="${MQTT_TLS_CLIENT_CERT:-/mosquitto/config/certs/test-client.crt}"
MQTT_TLS_CLIENT_KEY="${MQTT_TLS_CLIENT_KEY:-/mosquitto/config/certs/test-client.key}"

token=$(PROVISIONING_MASTER_KEY="${PROVISIONING_MASTER_KEY}" scripts/auth_token.sh verify-persistence operator home01 device:register 30)

curl -fsS -X POST "http://localhost:8081/devices/register" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${token}" \
  -d '{"id":"device-db-1","house":"home01","type":"relay_module","protocol":"wifi","capabilities":["relay_output"]}' >/tmp/register_db.json

docker exec smarthouse-mqtt sh -lc "mosquitto_pub --cafile ${MQTT_TLS_CA_CERT} --cert ${MQTT_TLS_CLIENT_CERT} --key ${MQTT_TLS_CLIENT_KEY} -p ${MQTT_TLS_PORT} -h localhost -t platform/home01/device-db-1/event -m '{\"event\":\"motion_detected\",\"value\":true}'"

sleep 1

echo "DEVICES_COUNT=$(docker exec smarthouse-postgres psql -U smarthouse -d smarthouse -t -A -c 'SELECT COUNT(*) FROM devices;')"
echo "REGISTRY_EVENTS_COUNT=$(docker exec smarthouse-postgres psql -U smarthouse -d smarthouse -t -A -c 'SELECT COUNT(*) FROM registry_events;')"
echo "AUTOMATION_EVENTS_COUNT=$(docker exec smarthouse-postgres psql -U smarthouse -d smarthouse -t -A -c 'SELECT COUNT(*) FROM automation_events;')"
echo "AUTOMATION_ACTIONS_COUNT=$(docker exec smarthouse-postgres psql -U smarthouse -d smarthouse -t -A -c 'SELECT COUNT(*) FROM automation_actions;')"
echo "DEAD_LETTERS_COUNT=$(docker exec smarthouse-postgres psql -U smarthouse -d smarthouse -t -A -c 'SELECT COUNT(*) FROM automation_dead_letters;')"
