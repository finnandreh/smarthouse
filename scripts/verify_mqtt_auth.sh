#!/usr/bin/env bash
set -euo pipefail

MQTT_TLS_PORT="${MQTT_TLS_PORT:-8883}"
MQTT_TLS_CA_CERT="${MQTT_TLS_CA_CERT:-/mosquitto/config/certs/ca.crt}"
MQTT_TLS_CLIENT_CERT="${MQTT_TLS_CLIENT_CERT:-/mosquitto/config/certs/test-client.crt}"
MQTT_TLS_CLIENT_KEY="${MQTT_TLS_CLIENT_KEY:-/mosquitto/config/certs/test-client.key}"

if docker exec smarthouse-mqtt sh -lc "mosquitto_pub --cafile ${MQTT_TLS_CA_CERT} -p ${MQTT_TLS_PORT} -h localhost -t platform/home01/authcheck/event -m '{\"event\":\"missing_client_cert\"}'" >/tmp/mqtt_no_client_cert.log 2>&1; then
  echo "NO_CLIENT_CERT_UNEXPECTED=success"
else
  echo "NO_CLIENT_CERT_EXPECTED=failure"
fi

if docker exec smarthouse-mqtt sh -lc "mosquitto_pub --cafile ${MQTT_TLS_CA_CERT} --cert ${MQTT_TLS_CLIENT_CERT} --key ${MQTT_TLS_CLIENT_KEY} -p ${MQTT_TLS_PORT} -h localhost -t platform/home01/authcheck/event -m '{\"event\":\"auth_ok\"}'" >/tmp/mqtt_auth.log 2>&1; then
  echo "AUTH_PUBLISH_EXPECTED=success"
else
  echo "AUTH_PUBLISH_UNEXPECTED=failure"
fi
