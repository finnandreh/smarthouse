#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8088}"

echo "[verify_installer_platform] Waiting for installer-platform readiness..."
for i in $(seq 1 30); do
  if curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "[verify_installer_platform] ERROR: installer-platform not ready"
    exit 1
  fi
  sleep 2
done

health_json=$(curl -fsS "$BASE_URL/health")
health_status=$(printf '%s' "$health_json" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status", ""))')
if [ "$health_status" != "ok" ]; then
  echo "[verify_installer_platform] ERROR: invalid health response"
  echo "$health_json"
  exit 1
fi

valid_payload='{
  "site_id": "site-alpha",
  "installer_id": "installer-1",
  "target": "edge-controller",
  "package_version": "1.2.3",
  "channel": "stable",
  "include_steps": ["precheck", "install", "postcheck"]
}'

validate_json=$(curl -fsS -X POST "$BASE_URL/install/validate" \
  -H "Content-Type: application/json" \
  -d "$valid_payload")

valid_flag=$(printf '%s' "$validate_json" | python3 -c 'import json,sys; print(str(json.load(sys.stdin).get("valid", False)).lower())')
if [ "$valid_flag" != "true" ]; then
  echo "[verify_installer_platform] ERROR: expected valid install payload"
  echo "$validate_json"
  exit 1
fi

plan_json=$(curl -fsS -X POST "$BASE_URL/install/plan" \
  -H "Content-Type: application/json" \
  -d "$valid_payload")

plan_target=$(printf '%s' "$plan_json" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("target", ""))')
if [ "$plan_target" != "edge-controller" ]; then
  echo "[verify_installer_platform] ERROR: unexpected plan target"
  echo "$plan_json"
  exit 1
fi

invalid_payload='{
  "site_id": "site-alpha",
  "installer_id": "installer-1",
  "target": "edge-controller-ha",
  "package_version": "1.2.3",
  "channel": "stable",
  "include_steps": ["install"]
}'

bad_validate_json=$(curl -fsS -X POST "$BASE_URL/install/validate" \
  -H "Content-Type: application/json" \
  -d "$invalid_payload")

bad_valid_flag=$(printf '%s' "$bad_validate_json" | python3 -c 'import json,sys; print(str(json.load(sys.stdin).get("valid", True)).lower())')
if [ "$bad_valid_flag" != "false" ]; then
  echo "[verify_installer_platform] ERROR: expected invalid HA validate payload"
  echo "$bad_validate_json"
  exit 1
fi

status_code=$(curl -sS -o /tmp/installer_bad_plan.json -w "%{http_code}" -X POST "$BASE_URL/install/plan" \
  -H "Content-Type: application/json" \
  -d "$invalid_payload")

if [ "$status_code" != "422" ]; then
  echo "[verify_installer_platform] ERROR: expected 422 for invalid plan, got $status_code"
  cat /tmp/installer_bad_plan.json || true
  exit 1
fi

error_code=$(python3 -c 'import json; print(json.load(open("/tmp/installer_bad_plan.json")).get("detail", {}).get("code", ""))')
if [ "$error_code" != "INVALID_INSTALL_PLAN" ]; then
  echo "[verify_installer_platform] ERROR: expected INVALID_INSTALL_PLAN, got '$error_code'"
  cat /tmp/installer_bad_plan.json || true
  exit 1
fi

echo "VERIFY_INSTALLER_PLATFORM=passed"
