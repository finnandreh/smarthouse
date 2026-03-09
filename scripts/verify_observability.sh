#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8094}"

echo "[verify_observability] Waiting for observability readiness..."
for i in $(seq 1 30); do
  if curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "[verify_observability] ERROR: observability service not ready"
    exit 1
  fi
  sleep 2
done

health_json=$(curl -fsS "$BASE_URL/health")
health_status=$(printf '%s' "$health_json" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status", ""))')
if [ "$health_status" != "ok" ]; then
  echo "[verify_observability] ERROR: invalid health response"
  echo "$health_json"
  exit 1
fi

valid_payload='{
  "environment": "local-dev",
  "scrape_targets": ["edge-controller", "device-registry", "automation-engine"]
}'

validate_json=$(curl -fsS -X POST "$BASE_URL/targets/validate" -H "Content-Type: application/json" -d "$valid_payload")
is_valid=$(printf '%s' "$validate_json" | python3 -c 'import json,sys; print(str(json.load(sys.stdin).get("valid", False)).lower())')
if [ "$is_valid" != "true" ]; then
  echo "[verify_observability] ERROR: expected valid target payload"
  echo "$validate_json"
  exit 1
fi

preview_json=$(curl -fsS -X POST "$BASE_URL/dashboards/preview" -H "Content-Type: application/json" -d "$valid_payload")
panel_count=$(printf '%s' "$preview_json" | python3 -c 'import json,sys; print(len(json.load(sys.stdin).get("panels", [])))')
if [ "$panel_count" -lt 3 ]; then
  echo "[verify_observability] ERROR: expected at least 3 panels"
  echo "$preview_json"
  exit 1
fi

invalid_payload='{
  "environment": "local-dev",
  "scrape_targets": ["automation-engine"]
}'

status_code=$(curl -sS -o /tmp/obs_bad.json -w "%{http_code}" -X POST "$BASE_URL/dashboards/preview" -H "Content-Type: application/json" -d "$invalid_payload")
if [ "$status_code" != "422" ]; then
  echo "[verify_observability] ERROR: expected 422 for invalid observability targets, got $status_code"
  cat /tmp/obs_bad.json || true
  exit 1
fi

error_code=$(python3 -c 'import json; print(json.load(open("/tmp/obs_bad.json")).get("detail", {}).get("code", ""))')
if [ "$error_code" != "INVALID_OBSERVABILITY_TARGETS" ]; then
  echo "[verify_observability] ERROR: expected INVALID_OBSERVABILITY_TARGETS, got '$error_code'"
  cat /tmp/obs_bad.json || true
  exit 1
fi

echo "VERIFY_OBSERVABILITY=passed"
