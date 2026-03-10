#!/usr/bin/env bash
set -euo pipefail

cd /mnt/c/smarthouse
MQTT_TLS_PORT="${MQTT_TLS_PORT:-8883}"
MQTT_TLS_CA_CERT="${MQTT_TLS_CA_CERT:-/mosquitto/config/certs/ca.crt}"
MQTT_TLS_CLIENT_CERT="${MQTT_TLS_CLIENT_CERT:-/mosquitto/config/certs/test-client.crt}"
MQTT_TLS_CLIENT_KEY="${MQTT_TLS_CLIENT_KEY:-/mosquitto/config/certs/test-client.key}"

stamp="$(date +%s)"
discovery_device_id="disc-${stamp}"
announce_device_id="announce-${stamp}"
house_id="home01"

for i in $(seq 1 30); do
  if curl -fsS "http://localhost:8081/health" >/dev/null 2>&1; then
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "[verify_registry_discovery_dual_path] ERROR: device-registry not ready"
    exit 1
  fi
  sleep 2
done

discovery_payload=$(cat <<JSON
{"device_id":"${discovery_device_id}","house":"${house_id}","device_type":"relay_module","protocol":"mqtt","firmware_version":"0.1.0","capabilities":["relay_output","power_monitor"]}
JSON
)

docker exec smarthouse-mqtt sh -lc "mosquitto_pub --cafile ${MQTT_TLS_CA_CERT} --cert ${MQTT_TLS_CLIENT_CERT} --key ${MQTT_TLS_CLIENT_KEY} -p ${MQTT_TLS_PORT} -h localhost -t platform/discovery -m '${discovery_payload}'"

announce_payload=$(cat <<JSON
{"event":"device_announce","type":"relay_module","protocol":"wifi","capabilities":["relay_output"]}
JSON
)

docker exec smarthouse-mqtt sh -lc "mosquitto_pub --cafile ${MQTT_TLS_CA_CERT} --cert ${MQTT_TLS_CLIENT_CERT} --key ${MQTT_TLS_CLIENT_KEY} -p ${MQTT_TLS_PORT} -h localhost -t platform/${house_id}/${announce_device_id}/event -m '${announce_payload}'"

sleep 2

discovery_device=$(curl -fsS "http://localhost:8081/devices/${discovery_device_id}")
announce_device=$(curl -fsS "http://localhost:8081/devices/${announce_device_id}")

actual_discovery_house=$(printf '%s' "${discovery_device}" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("house", ""))')
actual_announce_house=$(printf '%s' "${announce_device}" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("house", ""))')

if [ "${actual_discovery_house}" != "${house_id}" ]; then
  echo "[verify_registry_discovery_dual_path] ERROR: discovery path house mismatch"
  echo "${discovery_device}"
  exit 1
fi

if [ "${actual_announce_house}" != "${house_id}" ]; then
  echo "[verify_registry_discovery_dual_path] ERROR: announce path house mismatch"
  echo "${announce_device}"
  exit 1
fi

echo "VERIFY_REGISTRY_DISCOVERY_DUAL_PATH=passed"
