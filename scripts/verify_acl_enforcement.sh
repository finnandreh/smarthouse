#!/usr/bin/env bash
set -euo pipefail

MQTT_TLS_PORT="${MQTT_TLS_PORT:-8883}"
MQTT_TLS_CA_CERT="${MQTT_TLS_CA_CERT:-/mosquitto/config/certs/ca.crt}"

# Check blocked cross-topic publish by delivery observation.
rm -f /tmp/acl_blocked_delivery.txt
(
  docker exec smarthouse-mqtt sh -lc "timeout 4 mosquitto_sub --cafile ${MQTT_TLS_CA_CERT} --cert /mosquitto/config/certs/test-client.crt --key /mosquitto/config/certs/test-client.key -p ${MQTT_TLS_PORT} -h localhost -t platform/home01/bridge-modbus-01/event -C 1" >/tmp/acl_blocked_delivery.txt
) &
sub_blocked_pid=$!
sleep 1
docker exec smarthouse-mqtt sh -lc "mosquitto_pub --cafile ${MQTT_TLS_CA_CERT} --cert /mosquitto/config/certs/bridge-knx.crt --key /mosquitto/config/certs/bridge-knx.key -p ${MQTT_TLS_PORT} -h localhost -t platform/home01/bridge-modbus-01/event -m '{\"event\":\"acl_should_fail\"}'" >/tmp/acl_blocked_publish.log 2>&1 || true
wait "$sub_blocked_pid" || true

if [ -s /tmp/acl_blocked_delivery.txt ]; then
  echo "ACL_UNEXPECTED=bridge_knx_can_write_modbus"
  exit 1
fi

# Check allowed own-topic publish by delivery observation.
rm -f /tmp/acl_allowed_delivery.txt
(
  docker exec smarthouse-mqtt sh -lc "timeout 4 mosquitto_sub --cafile ${MQTT_TLS_CA_CERT} --cert /mosquitto/config/certs/test-client.crt --key /mosquitto/config/certs/test-client.key -p ${MQTT_TLS_PORT} -h localhost -t platform/home01/bridge-knx-01/event -C 1" >/tmp/acl_allowed_delivery.txt
) &
sub_allowed_pid=$!
sleep 1
docker exec smarthouse-mqtt sh -lc "mosquitto_pub --cafile ${MQTT_TLS_CA_CERT} --cert /mosquitto/config/certs/bridge-knx.crt --key /mosquitto/config/certs/bridge-knx.key -p ${MQTT_TLS_PORT} -h localhost -t platform/home01/bridge-knx-01/event -m '{\"event\":\"acl_allowed\"}'" >/tmp/acl_allowed_publish.log 2>&1
wait "$sub_allowed_pid"

if [ ! -s /tmp/acl_allowed_delivery.txt ]; then
  echo "ACL_UNEXPECTED=bridge_knx_cannot_write_own_topic"
  exit 1
fi

echo "ACL_EXPECTED=bridge_knx_restricted_and_valid"
