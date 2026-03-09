#!/usr/bin/env bash
set -euo pipefail

cd /mnt/c/smarthouse

REQUIRE_INTEGRATION="${REQUIRE_DEVICE_SDK_MQTT_INTEGRATION:-0}"

fail_or_skip() {
  local reason="$1"
  echo "DEVICE_SDK_MQTT_INTEGRATION=${reason}"
  if [[ "${REQUIRE_INTEGRATION}" == "1" ]]; then
    echo "VERIFY_DEVICE_SDK_MQTT_INTEGRATION=failed"
    exit 1
  fi
  echo "VERIFY_DEVICE_SDK_MQTT_INTEGRATION=skipped"
  exit 0
}

PYTHON_BIN="python3"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "python3 not found"
  exit 1
fi

DEVICE_RUNNER="local"
DEVICE_MQTT_HOST="localhost"
DEVICE_CA_CERT="certs/ca.crt"
DEVICE_CLIENT_CERT="certs/esp32-simulator.crt"
DEVICE_CLIENT_KEY="certs/esp32-simulator.key"

if ! "${PYTHON_BIN}" - <<'PY' >/dev/null 2>&1
import paho.mqtt.client  # noqa: F401
PY
then
  if ! "${PYTHON_BIN}" -m pip --version >/dev/null 2>&1; then
    "${PYTHON_BIN}" -m ensurepip --upgrade >/dev/null 2>&1 || true
  fi

  if ! "${PYTHON_BIN}" -m pip --version >/dev/null 2>&1; then
    DEVICE_RUNNER="container"
  elif ! "${PYTHON_BIN}" -m pip install --quiet -r device_sdk/requirements.txt; then
    DEVICE_RUNNER="container"
  fi
fi

if [[ "${DEVICE_RUNNER}" == "container" ]]; then
  if ! docker network inspect smarthouse_default >/dev/null 2>&1; then
    fail_or_skip "failed_no_stack_network"
  fi
  DEVICE_MQTT_HOST="mqtt"
  DEVICE_CA_CERT="/workspace/certs/ca.crt"
  DEVICE_CLIENT_CERT="/workspace/certs/esp32-simulator.crt"
  DEVICE_CLIENT_KEY="/workspace/certs/esp32-simulator.key"
fi

MQTT_TLS_PORT="${MQTT_TLS_PORT:-8883}"
MQTT_TLS_CA_CERT="${MQTT_TLS_CA_CERT:-/mosquitto/config/certs/ca.crt}"
MQTT_TLS_CLIENT_CERT="${MQTT_TLS_CLIENT_CERT:-/mosquitto/config/certs/test-client.crt}"
MQTT_TLS_CLIENT_KEY="${MQTT_TLS_CLIENT_KEY:-/mosquitto/config/certs/test-client.key}"

RUN_SUFFIX="$(date +%s%N)"
HOUSE_ID="home01"
DEVICE_ID="device123"
EVENT_TOPIC="platform/${HOUSE_ID}/${DEVICE_ID}/event"
CONTROL_TOPIC="platform/${HOUSE_ID}/${DEVICE_ID}/control"

EVENT_LOG="/tmp/sdk_int_events.log"
DEVICE_LOG="/tmp/sdk_int_device.log"
rm -f "${EVENT_LOG}" "${DEVICE_LOG}"

cleanup() {
  if [[ -n "${DEVICE_PID:-}" ]] && kill -0 "${DEVICE_PID}" >/dev/null 2>&1; then
    kill "${DEVICE_PID}" >/dev/null 2>&1 || true
  fi
  if [[ -n "${SUB_PID:-}" ]] && kill -0 "${SUB_PID}" >/dev/null 2>&1; then
    kill "${SUB_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

(
  docker exec smarthouse-mqtt sh -lc "timeout 30 mosquitto_sub --cafile ${MQTT_TLS_CA_CERT} --cert ${MQTT_TLS_CLIENT_CERT} --key ${MQTT_TLS_CLIENT_KEY} -p ${MQTT_TLS_PORT} -h localhost -t ${EVENT_TOPIC} -C 12" >"${EVENT_LOG}"
) &
SUB_PID=$!

sleep 1
if [[ "${DEVICE_RUNNER}" == "local" ]]; then
  "${PYTHON_BIN}" -m device_sdk.examples.local_device \
    --target esp32 \
    --house "${HOUSE_ID}" \
    --device-id "${DEVICE_ID}" \
    --mqtt-host "${DEVICE_MQTT_HOST}" \
    --mqtt-port 8883 \
    --ca-cert "${DEVICE_CA_CERT}" \
    --client-cert "${DEVICE_CLIENT_CERT}" \
    --client-key "${DEVICE_CLIENT_KEY}" \
    --interval-seconds 0.6 \
    --max-iterations 10 >"${DEVICE_LOG}" 2>&1 &
else
  docker run --rm --network smarthouse_default \
    -v /mnt/c/smarthouse:/workspace \
    -w /workspace \
    python:3.12-slim sh -lc "pip install --quiet -r device_sdk/requirements.txt && python -m device_sdk.examples.local_device --target esp32 --house ${HOUSE_ID} --device-id ${DEVICE_ID} --mqtt-host ${DEVICE_MQTT_HOST} --mqtt-port 8883 --ca-cert ${DEVICE_CA_CERT} --client-cert ${DEVICE_CLIENT_CERT} --client-key ${DEVICE_CLIENT_KEY} --interval-seconds 0.6 --max-iterations 10" >"${DEVICE_LOG}" 2>&1 &
fi
DEVICE_PID=$!

announce_seen=0
for _ in $(seq 1 40); do
  if [[ -s "${EVENT_LOG}" ]] && grep -q '"event": "device_announce"' "${EVENT_LOG}"; then
    announce_seen=1
    break
  fi
  sleep 0.5
done

if [[ "${announce_seen}" -ne 1 ]]; then
  echo "SDK integration verifier failed: device announce was not observed before control publish"
  exit 1
fi

docker exec smarthouse-mqtt sh -lc "mosquitto_pub --cafile ${MQTT_TLS_CA_CERT} --cert ${MQTT_TLS_CLIENT_CERT} --key ${MQTT_TLS_CLIENT_KEY} -p ${MQTT_TLS_PORT} -h localhost -t ${CONTROL_TOPIC} -m '{\"action\":\"set_relay\",\"value\":\"ON\"}'"

wait "${DEVICE_PID}"
wait "${SUB_PID}"

"${PYTHON_BIN}" - <<'PY'
import json
from pathlib import Path

event_log = Path("/tmp/sdk_int_events.log")
lines = [line.strip() for line in event_log.read_text(encoding="utf-8").splitlines() if line.strip()]
if not lines:
    raise SystemExit("No event messages received from SDK device")

messages = []
for raw in lines:
    try:
        messages.append(json.loads(raw))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON event payload: {raw} ({exc})") from exc

has_announce = any(msg.get("event") == "device_announce" for msg in messages)
has_ack_on = any(
    msg.get("event") == "control_ack"
    and msg.get("applied") is True
    and msg.get("action") == "set_relay"
    for msg in messages
)
has_relay_on = any(msg.get("event") == "relay_state" and str(msg.get("value")) == "ON" for msg in messages)

if not has_announce:
    raise SystemExit("Missing device_announce event")
if not has_ack_on:
    raise SystemExit("Missing successful control_ack for set_relay")
if not has_relay_on:
    raise SystemExit("Missing relay_state event with value ON")

print("DEVICE_SDK_MQTT_INTEGRATION=passed")
PY

echo "DEVICE_SDK_MQTT_INTEGRATION_RUNNER=${DEVICE_RUNNER}"
echo "VERIFY_DEVICE_SDK_MQTT_INTEGRATION=passed"
