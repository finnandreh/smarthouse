#!/usr/bin/env bash
set -euo pipefail

PROJECT_ENGINE_URL="${PROJECT_ENGINE_URL:-http://localhost:8085}"
SYSTEM_GENERATOR_URL="${SYSTEM_GENERATOR_URL:-http://localhost:8086}"

for _ in $(seq 1 30); do
  if curl -fsS "${SYSTEM_GENERATOR_URL}/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

SG_HEALTH=$(curl -fsS "${SYSTEM_GENERATOR_URL}/health")
echo "SYSTEM_GENERATOR_HEALTH=${SG_HEALTH}"

PROJECT_CREATE=$(curl -fsS -X POST "${PROJECT_ENGINE_URL}/projects" \
  -H "Content-Type: application/json" \
  -d '{
    "house_id": "home01",
    "project_name": "generator-smoke",
    "zones": [
      {
        "zone_id": "hall",
        "name": "Hall",
        "devices": [
          {
            "device_id": "hall-relay-01",
            "device_type": "relay_module",
            "protocol": "wifi",
            "capabilities": ["relay_output", "power_monitor"]
          }
        ]
      }
    ]
  }')

PROJECT_ID=$(echo "${PROJECT_CREATE}" | sed -n 's/.*"project_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
if [[ -z "${PROJECT_ID}" ]]; then
  echo "Failed to parse project id for system generator verification"
  exit 1
fi

CONTRACT=$(curl -fsS "${PROJECT_ENGINE_URL}/projects/${PROJECT_ID}/generation-contract")
VALIDATE_BODY=$(curl -fsS -X POST "${SYSTEM_GENERATOR_URL}/validate" \
  -H "Content-Type: application/json" \
  -d "${CONTRACT}")

if ! echo "${VALIDATE_BODY}" | grep -q '"valid":true'; then
  echo "Expected system-generator validate to return valid=true"
  echo "Validate body: ${VALIDATE_BODY}"
  exit 1
fi

GENERATE_BODY=$(curl -fsS -X POST "${SYSTEM_GENERATOR_URL}/generate" \
  -H "Content-Type: application/json" \
  -d "{\"contract\":${CONTRACT},\"mode\":\"dry-run\"}")

if ! echo "${GENERATE_BODY}" | grep -q '"artifact_plan"'; then
  echo "Expected generation response to include artifact_plan"
  echo "Generate body: ${GENERATE_BODY}"
  exit 1
fi

BAD_CONTRACT='{"project_id":"bad","contract_version":"phase7-v1","generated_at":"2026-01-01T00:00:00Z","devices_by_protocol":{"zigbee":[]},"zone_count":1}'
INVALID_VALIDATE=$(curl -fsS -X POST "${SYSTEM_GENERATOR_URL}/validate" -H "Content-Type: application/json" -d "${BAD_CONTRACT}")
if ! echo "${INVALID_VALIDATE}" | grep -q '"valid":false'; then
  echo "Expected invalid contract validation to return valid=false"
  echo "Invalid validate body: ${INVALID_VALIDATE}"
  exit 1
fi

INVALID_GENERATE_CODE=$(curl -s -o /tmp/system_generator_invalid_generate.json -w "%{http_code}" -X POST "${SYSTEM_GENERATOR_URL}/generate" \
  -H "Content-Type: application/json" \
  -d "{\"contract\":${BAD_CONTRACT},\"mode\":\"dry-run\"}")
if [[ "${INVALID_GENERATE_CODE}" != "422" ]]; then
  echo "Expected 422 from invalid contract generation, got ${INVALID_GENERATE_CODE}"
  echo "Invalid generate body: $(cat /tmp/system_generator_invalid_generate.json)"
  exit 1
fi

echo "SYSTEM_GENERATOR_PROJECT_CREATE=${PROJECT_CREATE}"
echo "SYSTEM_GENERATOR_CONTRACT=${CONTRACT}"
echo "SYSTEM_GENERATOR_VALIDATE=${VALIDATE_BODY}"
echo "SYSTEM_GENERATOR_GENERATE=${GENERATE_BODY}"
echo "SYSTEM_GENERATOR_INVALID_VALIDATE=${INVALID_VALIDATE}"
echo "SYSTEM_GENERATOR_INVALID_GENERATE_CODE=${INVALID_GENERATE_CODE}"
echo "VERIFY_SYSTEM_GENERATOR=passed"
