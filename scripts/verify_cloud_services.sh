#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8087}"

echo "[verify_cloud_services] Waiting for cloud-services readiness..."
for i in $(seq 1 30); do
  if curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "[verify_cloud_services] ERROR: cloud-services not ready"
    exit 1
  fi
  sleep 2
done

health_json=$(curl -fsS "$BASE_URL/health")
health_status=$(printf '%s' "$health_json" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status", ""))')
local_first=$(printf '%s' "$health_json" | python3 -c 'import json,sys; print(str(json.load(sys.stdin).get("local_first_core_unchanged", "")).lower())')

if [ "$health_status" != "ok" ] || [ "$local_first" != "true" ]; then
  echo "[verify_cloud_services] ERROR: health contract mismatch"
  echo "$health_json"
  exit 1
fi

preview_payload='{
  "site_id": "site-alpha",
  "tenant_id": "tenant-local",
  "mode": "metadata-only",
  "include_sections": ["devices", "automation"]
}'

preview_json=$(curl -fsS -X POST "$BASE_URL/sync/preview" \
  -H "Content-Type: application/json" \
  -d "$preview_payload")

preview_mode=$(printf '%s' "$preview_json" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("mode", ""))')
record_count=$(printf '%s' "$preview_json" | python3 -c 'import json,sys; print(int(json.load(sys.stdin).get("estimated_records", 0)))')

if [ "$preview_mode" != "metadata-only" ] || [ "$record_count" -le 0 ]; then
  echo "[verify_cloud_services] ERROR: preview response invalid"
  echo "$preview_json"
  exit 1
fi

bad_payload='{
  "site_id": "site-alpha",
  "tenant_id": "tenant-local",
  "mode": "telemetry-summary",
  "include_sections": ["devices"]
}'

status_code=$(curl -sS -o /tmp/cloud_bad.json -w "%{http_code}" -X POST "$BASE_URL/sync/preview" \
  -H "Content-Type: application/json" \
  -d "$bad_payload")

if [ "$status_code" != "422" ]; then
  echo "[verify_cloud_services] ERROR: expected 422 for invalid telemetry request, got $status_code"
  cat /tmp/cloud_bad.json || true
  exit 1
fi

error_code=$(python3 -c 'import json; print(json.load(open("/tmp/cloud_bad.json")).get("detail", {}).get("code", ""))')
if [ "$error_code" != "INVALID_SYNC_REQUEST" ]; then
  echo "[verify_cloud_services] ERROR: expected INVALID_SYNC_REQUEST, got '$error_code'"
  cat /tmp/cloud_bad.json || true
  exit 1
fi

echo "VERIFY_CLOUD_SERVICES=passed"
