#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8089}"

echo "[verify_telemetry] Waiting for telemetry readiness..."
for i in $(seq 1 30); do
  if curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "[verify_telemetry] ERROR: telemetry not ready"
    exit 1
  fi
  sleep 2
done

health_json=$(curl -fsS "$BASE_URL/health")
health_status=$(printf '%s' "$health_json" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status", ""))')
if [ "$health_status" != "ok" ]; then
  echo "[verify_telemetry] ERROR: invalid health response"
  echo "$health_json"
  exit 1
fi

valid_payload='{
  "house_id": "home01",
  "source_protocol": "mqtt",
  "points": [
    {"name": "temperature_c", "value": 21.7, "unit": "C"},
    {"name": "power_w", "value": 312.2, "unit": "W"}
  ]
}'

validate_json=$(curl -fsS -X POST "$BASE_URL/ingest/validate" -H "Content-Type: application/json" -d "$valid_payload")
is_valid=$(printf '%s' "$validate_json" | python3 -c 'import json,sys; print(str(json.load(sys.stdin).get("valid", False)).lower())')
if [ "$is_valid" != "true" ]; then
  echo "[verify_telemetry] ERROR: expected valid payload"
  echo "$validate_json"
  exit 1
fi

ingest_json=$(curl -fsS -X POST "$BASE_URL/ingest/batch" -H "Content-Type: application/json" -d "$valid_payload")
point_count=$(printf '%s' "$ingest_json" | python3 -c 'import json,sys; print(int(json.load(sys.stdin).get("point_count", 0)))')
if [ "$point_count" -lt 2 ]; then
  echo "[verify_telemetry] ERROR: expected point_count >= 2"
  echo "$ingest_json"
  exit 1
fi

invalid_payload='{
  "house_id": "home01",
  "source_protocol": "mqtt",
  "points": [
    {"name": "debug_temp", "value": 21.0, "unit": "C"}
  ]
}'

status_code=$(curl -sS -o /tmp/telemetry_bad.json -w "%{http_code}" -X POST "$BASE_URL/ingest/batch" -H "Content-Type: application/json" -d "$invalid_payload")
if [ "$status_code" != "422" ]; then
  echo "[verify_telemetry] ERROR: expected 422 for invalid ingest, got $status_code"
  cat /tmp/telemetry_bad.json || true
  exit 1
fi

error_code=$(python3 -c 'import json; print(json.load(open("/tmp/telemetry_bad.json")).get("detail", {}).get("code", ""))')
if [ "$error_code" != "INVALID_TELEMETRY_BATCH" ]; then
  echo "[verify_telemetry] ERROR: expected INVALID_TELEMETRY_BATCH, got '$error_code'"
  cat /tmp/telemetry_bad.json || true
  exit 1
fi

echo "VERIFY_TELEMETRY=passed"
