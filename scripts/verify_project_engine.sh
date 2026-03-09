#!/usr/bin/env bash
set -euo pipefail

PROJECT_ENGINE_URL="${PROJECT_ENGINE_URL:-http://localhost:8085}"

for _ in $(seq 1 30); do
  if curl -fsS "${PROJECT_ENGINE_URL}/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

HEALTH_BODY=$(curl -fsS "${PROJECT_ENGINE_URL}/health")

echo "PROJECT_ENGINE_HEALTH=${HEALTH_BODY}"

if ! echo "${HEALTH_BODY}" | grep -q '"status"'; then
  echo "Project engine health response missing status field"
  exit 1
fi

CREATE_BODY=$(curl -fsS -X POST "${PROJECT_ENGINE_URL}/projects" \
  -H "Content-Type: application/json" \
  -d '{
    "house_id": "home01",
    "project_name": "scaffold-smoke",
    "zones": [
      {
        "zone_id": "living-room",
        "name": "Living Room",
        "devices": [
          {
            "device_id": "lr-relay-01",
            "device_type": "relay_module",
            "protocol": "wifi",
            "capabilities": ["relay_output"]
          }
        ]
      }
    ]
  }')

VALIDATE_OK_BODY=$(curl -fsS -X POST "${PROJECT_ENGINE_URL}/projects/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "house_id": "home01",
    "project_name": "validate-ok",
    "zones": [
      {
        "zone_id": "kitchen",
        "name": "Kitchen",
        "devices": [
          {
            "device_id": "kitchen-relay-01",
            "device_type": "relay_module",
            "protocol": "wifi",
            "capabilities": ["relay_output", "power_monitor"]
          }
        ]
      }
    ]
  }')

if ! echo "${VALIDATE_OK_BODY}" | grep -q '"valid":true'; then
  echo "Expected valid=true from /projects/validate for supported payload"
  echo "Validate OK body: ${VALIDATE_OK_BODY}"
  exit 1
fi

VALIDATE_BAD_BODY=$(curl -fsS -X POST "${PROJECT_ENGINE_URL}/projects/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "house_id": "home01",
    "project_name": "validate-bad",
    "zones": [
      {
        "zone_id": "garage",
        "name": "Garage",
        "devices": [
          {
            "device_id": "garage-unknown-01",
            "device_type": "unknown_type",
            "protocol": "wifi",
            "capabilities": ["relay_output"]
          },
          {
            "device_id": "garage-thermo-01",
            "device_type": "thermostat",
            "protocol": "wifi",
            "capabilities": ["relay_output"]
          }
        ]
      }
    ]
  }')

if ! echo "${VALIDATE_BAD_BODY}" | grep -q '"valid":false'; then
  echo "Expected valid=false from /projects/validate for unsupported payload"
  echo "Validate bad body: ${VALIDATE_BAD_BODY}"
  exit 1
fi

if ! echo "${VALIDATE_BAD_BODY}" | grep -q 'unsupported_device_type\|unsupported_capabilities'; then
  echo "Expected structured validation errors in /projects/validate response"
  echo "Validate bad body: ${VALIDATE_BAD_BODY}"
  exit 1
fi

PROJECT_ID=$(echo "${CREATE_BODY}" | sed -n 's/.*"project_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
if [[ -z "${PROJECT_ID}" ]]; then
  echo "Failed to parse project_id from project-engine response"
  exit 1
fi

CONTRACT_BODY=$(curl -fsS "${PROJECT_ENGINE_URL}/projects/${PROJECT_ID}/generation-contract")
LIST_BODY=$(curl -fsS "${PROJECT_ENGINE_URL}/projects")

if ! echo "${CONTRACT_BODY}" | grep -q '"contract_version"'; then
  echo "Project engine generation contract missing contract_version"
  exit 1
fi

if ! echo "${CONTRACT_BODY}" | grep -q '"devices_by_protocol"'; then
  echo "Project engine generation contract missing devices_by_protocol"
  exit 1
fi

INVALID_CREATE_CODE=$(curl -s -o /tmp/project_engine_invalid_create.json -w "%{http_code}" -X POST "${PROJECT_ENGINE_URL}/projects" \
  -H "Content-Type: application/json" \
  -d '{"house_id":"home01","project_name":"bad-project","zones":[{"zone_id":"bad-zone","name":"Bad Zone","devices":[{"device_id":"d1","device_type":"relay_module","protocol":"zigbee","capabilities":["relay_output"]}]}]}')

if [[ "${INVALID_CREATE_CODE}" != "422" ]]; then
  echo "Expected 422 for invalid protocol payload, got ${INVALID_CREATE_CODE}"
  echo "Invalid create body: $(cat /tmp/project_engine_invalid_create.json)"
  exit 1
fi

MISSING_PROJECT_CODE=$(curl -s -o /tmp/project_engine_missing_project.json -w "%{http_code}" "${PROJECT_ENGINE_URL}/projects/not-found/generation-contract")
if [[ "${MISSING_PROJECT_CODE}" != "404" ]]; then
  echo "Expected 404 for missing project generation contract, got ${MISSING_PROJECT_CODE}"
  echo "Missing project body: $(cat /tmp/project_engine_missing_project.json)"
  exit 1
fi

echo "PROJECT_ENGINE_CREATE=${CREATE_BODY}"
echo "PROJECT_ENGINE_VALIDATE_OK=${VALIDATE_OK_BODY}"
echo "PROJECT_ENGINE_VALIDATE_BAD=${VALIDATE_BAD_BODY}"
echo "PROJECT_ENGINE_CONTRACT=${CONTRACT_BODY}"
echo "PROJECT_ENGINE_LIST=${LIST_BODY}"
echo "PROJECT_ENGINE_INVALID_CREATE_CODE=${INVALID_CREATE_CODE}"
echo "PROJECT_ENGINE_MISSING_PROJECT_CODE=${MISSING_PROJECT_CODE}"
echo "VERIFY_PROJECT_ENGINE=passed"
