#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8090}"

echo "[verify_ai_service] Waiting for ai readiness..."
for i in $(seq 1 30); do
  if curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "[verify_ai_service] ERROR: ai service not ready"
    exit 1
  fi
  sleep 2
done

health_json=$(curl -fsS "$BASE_URL/health")
health_status=$(printf '%s' "$health_json" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status", ""))')
if [ "$health_status" != "ok" ]; then
  echo "[verify_ai_service] ERROR: invalid health response"
  echo "$health_json"
  exit 1
fi

valid_payload='{
  "project_id": "project-123",
  "objective": "energy",
  "horizon_hours": 24,
  "signals": ["power_price", "weather"]
}'

validate_json=$(curl -fsS -X POST "$BASE_URL/optimize/validate" -H "Content-Type: application/json" -d "$valid_payload")
is_valid=$(printf '%s' "$validate_json" | python3 -c 'import json,sys; print(str(json.load(sys.stdin).get("valid", False)).lower())')
if [ "$is_valid" != "true" ]; then
  echo "[verify_ai_service] ERROR: expected valid payload"
  echo "$validate_json"
  exit 1
fi

plan_json=$(curl -fsS -X POST "$BASE_URL/optimize/plan" -H "Content-Type: application/json" -d "$valid_payload")
objective=$(printf '%s' "$plan_json" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("objective", ""))')
if [ "$objective" != "energy" ]; then
  echo "[verify_ai_service] ERROR: unexpected plan response"
  echo "$plan_json"
  exit 1
fi

invalid_payload='{
  "project_id": "project-123",
  "objective": "energy",
  "horizon_hours": 24,
  "signals": ["weather"]
}'

status_code=$(curl -sS -o /tmp/ai_bad.json -w "%{http_code}" -X POST "$BASE_URL/optimize/plan" -H "Content-Type: application/json" -d "$invalid_payload")
if [ "$status_code" != "422" ]; then
  echo "[verify_ai_service] ERROR: expected 422 for invalid optimization request, got $status_code"
  cat /tmp/ai_bad.json || true
  exit 1
fi

error_code=$(python3 -c 'import json; print(json.load(open("/tmp/ai_bad.json")).get("detail", {}).get("code", ""))')
if [ "$error_code" != "INVALID_OPTIMIZATION_REQUEST" ]; then
  echo "[verify_ai_service] ERROR: expected INVALID_OPTIMIZATION_REQUEST, got '$error_code'"
  cat /tmp/ai_bad.json || true
  exit 1
fi

echo "VERIFY_AI_SERVICE=passed"
