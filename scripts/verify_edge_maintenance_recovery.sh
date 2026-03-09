#!/usr/bin/env bash
set -euo pipefail

EDGE_API_KEY="${EDGE_API_KEY:-changeme-edge-local-dev}"
EDGE_API_KEY_OPERATOR="${EDGE_API_KEY_OPERATOR:-changeme-edge-operator-local-dev}"
RUN_SUFFIX="$(date +%s%N)"

DEVICE_BLOCKED_ID="edge-maint-recovery-blocked-${RUN_SUFFIX}"
DEVICE_RECOVERY_ID="edge-maint-recovery-ok-${RUN_SUFFIX}"

for i in $(seq 1 30); do
  if curl -fsS http://localhost:8084/health >/dev/null; then
    break
  fi
  sleep 2
done

status_before=$(curl -fsS http://localhost:8084/maintenance/status -H "x-edge-api-key: ${EDGE_API_KEY}")

enable_resp=$(curl -fsS -X POST http://localhost:8084/maintenance/enable \
  -H "Content-Type: application/json" \
  -H "x-edge-api-key: ${EDGE_API_KEY}" \
  -d '{"reason":"verify_maintenance_recovery"}')

status_enabled=$(curl -fsS http://localhost:8084/maintenance/status -H "x-edge-api-key: ${EDGE_API_KEY}")

code_provision_blocked=$(curl -s -o /tmp/edge_maint_recovery_provision_blocked.json -w "%{http_code}" -X POST \
  http://localhost:8084/provision/device \
  -H "Content-Type: application/json" \
  -H "x-edge-api-key: ${EDGE_API_KEY}" \
  -d '{"id":"'"${DEVICE_BLOCKED_ID}"'","house":"home01","type":"relay_module","protocol":"wifi","capabilities":["relay_output"]}')

code_prepare_blocked=$(curl -s -o /tmp/edge_maint_recovery_prepare_blocked.json -w "%{http_code}" -X POST \
  http://localhost:8084/provision/session/prepare \
  -H "Content-Type: application/json" \
  -H "x-edge-api-key: ${EDGE_API_KEY}" \
  -d '{"id":"'"${DEVICE_BLOCKED_ID}"'","house":"home01","type":"relay_module","protocol":"wifi","capabilities":["relay_output"],"installer_id":"edge-maint-recovery"}')

code_reload_blocked=$(curl -s -o /tmp/edge_maint_recovery_reload_blocked.json -w "%{http_code}" -X POST \
  http://localhost:8084/lifecycle/reload-automation \
  -H "x-edge-api-key: ${EDGE_API_KEY}")

code_bridge_blocked=$(curl -s -o /tmp/edge_maint_recovery_bridge_blocked.json -w "%{http_code}" -X POST \
  http://localhost:8084/lifecycle/bridges/modbus/reload \
  -H "x-edge-api-key: ${EDGE_API_KEY}")

code_config_read_during_maint=$(curl -s -o /tmp/edge_maint_recovery_config_read.json -w "%{http_code}" -X GET \
  http://localhost:8084/config \
  -H "x-edge-api-key: ${EDGE_API_KEY}")

code_state_read_during_maint=$(curl -s -o /tmp/edge_maint_recovery_state_read.json -w "%{http_code}" -X GET \
  http://localhost:8084/state/desired \
  -H "x-edge-api-key: ${EDGE_API_KEY}")

code_history_read_during_maint=$(curl -s -o /tmp/edge_maint_recovery_history_read.json -w "%{http_code}" -X GET \
  http://localhost:8084/reconcile/history \
  -H "x-edge-api-key: ${EDGE_API_KEY}")

code_operator_disable=$(curl -s -o /tmp/edge_maint_recovery_operator_disable.json -w "%{http_code}" -X POST \
  http://localhost:8084/maintenance/disable \
  -H "x-edge-api-key: ${EDGE_API_KEY_OPERATOR}")

disable_resp=$(curl -fsS -X POST http://localhost:8084/maintenance/disable -H "x-edge-api-key: ${EDGE_API_KEY}")
status_after=$(curl -fsS http://localhost:8084/maintenance/status -H "x-edge-api-key: ${EDGE_API_KEY}")

code_provision_recovered=$(curl -s -o /tmp/edge_maint_recovery_provision_ok.json -w "%{http_code}" -X POST \
  http://localhost:8084/provision/device \
  -H "Content-Type: application/json" \
  -H "x-edge-api-key: ${EDGE_API_KEY}" \
  -d '{"id":"'"${DEVICE_RECOVERY_ID}"'","house":"home01","type":"relay_module","protocol":"wifi","capabilities":["relay_output"]}')

code_reload_recovered=$(curl -s -o /tmp/edge_maint_recovery_reload_ok.json -w "%{http_code}" -X POST \
  http://localhost:8084/lifecycle/reload-automation \
  -H "x-edge-api-key: ${EDGE_API_KEY}")

code_bridge_recovered=$(curl -s -o /tmp/edge_maint_recovery_bridge_ok.json -w "%{http_code}" -X POST \
  http://localhost:8084/lifecycle/bridges/modbus/reload \
  -H "x-edge-api-key: ${EDGE_API_KEY}")

if ! printf '%s' "${status_before}" | grep -q '"enabled":false'; then
  echo "MAINT_RECOVERY_INITIAL_STATUS_UNEXPECTED"
  exit 1
fi
if ! printf '%s' "${status_enabled}" | grep -q '"enabled":true'; then
  echo "MAINT_RECOVERY_ENABLE_STATUS_UNEXPECTED"
  exit 1
fi
if [ "${code_provision_blocked}" != "423" ] || [ "${code_prepare_blocked}" != "423" ] || [ "${code_reload_blocked}" != "423" ] || [ "${code_bridge_blocked}" != "423" ]; then
  echo "MAINT_RECOVERY_BLOCKING_UNEXPECTED"
  exit 1
fi
if [ "${code_config_read_during_maint}" != "200" ] || [ "${code_state_read_during_maint}" != "200" ] || [ "${code_history_read_during_maint}" != "200" ]; then
  echo "MAINT_RECOVERY_READS_BLOCKED_UNEXPECTED"
  exit 1
fi
if [ "${code_operator_disable}" != "403" ]; then
  echo "MAINT_RECOVERY_OPERATOR_DISABLE_EXPECTED_403_GOT_${code_operator_disable}"
  exit 1
fi
if ! printf '%s' "${status_after}" | grep -q '"enabled":false'; then
  echo "MAINT_RECOVERY_DISABLE_STATUS_UNEXPECTED"
  exit 1
fi
if [ "${code_provision_recovered}" != "200" ] || [ "${code_reload_recovered}" != "200" ] || [ "${code_bridge_recovered}" != "200" ]; then
  echo "MAINT_RECOVERY_POST_DISABLE_UNEXPECTED"
  exit 1
fi

echo "MAINT_RECOVERY_STATUS_BEFORE=${status_before}"
echo "MAINT_RECOVERY_ENABLE_RESPONSE=${enable_resp}"
echo "MAINT_RECOVERY_STATUS_ENABLED=${status_enabled}"
echo "MAINT_RECOVERY_BLOCKED_PROVISION_CODE=${code_provision_blocked}"
echo "MAINT_RECOVERY_BLOCKED_PREPARE_CODE=${code_prepare_blocked}"
echo "MAINT_RECOVERY_BLOCKED_RELOAD_CODE=${code_reload_blocked}"
echo "MAINT_RECOVERY_BLOCKED_BRIDGE_CODE=${code_bridge_blocked}"
echo "MAINT_RECOVERY_READ_CONFIG_CODE=${code_config_read_during_maint}"
echo "MAINT_RECOVERY_READ_STATE_CODE=${code_state_read_during_maint}"
echo "MAINT_RECOVERY_READ_HISTORY_CODE=${code_history_read_during_maint}"
echo "MAINT_RECOVERY_OPERATOR_DISABLE_CODE=${code_operator_disable}"
echo "MAINT_RECOVERY_DISABLE_RESPONSE=${disable_resp}"
echo "MAINT_RECOVERY_STATUS_AFTER=${status_after}"
echo "MAINT_RECOVERY_RECOVERED_PROVISION_CODE=${code_provision_recovered}"
echo "MAINT_RECOVERY_RECOVERED_RELOAD_CODE=${code_reload_recovered}"
echo "MAINT_RECOVERY_RECOVERED_BRIDGE_CODE=${code_bridge_recovered}"
echo "MAINT_RECOVERY_BLOCKED_PROVISION_BODY=$(cat /tmp/edge_maint_recovery_provision_blocked.json)"
echo "MAINT_RECOVERY_BLOCKED_PREPARE_BODY=$(cat /tmp/edge_maint_recovery_prepare_blocked.json)"
echo "MAINT_RECOVERY_BLOCKED_RELOAD_BODY=$(cat /tmp/edge_maint_recovery_reload_blocked.json)"
echo "MAINT_RECOVERY_BLOCKED_BRIDGE_BODY=$(cat /tmp/edge_maint_recovery_bridge_blocked.json)"
echo "MAINT_RECOVERY_OPERATOR_DISABLE_BODY=$(cat /tmp/edge_maint_recovery_operator_disable.json)"
echo "MAINT_RECOVERY_RECOVERED_PROVISION_BODY=$(cat /tmp/edge_maint_recovery_provision_ok.json)"
echo "MAINT_RECOVERY_RECOVERED_RELOAD_BODY=$(cat /tmp/edge_maint_recovery_reload_ok.json)"
echo "MAINT_RECOVERY_RECOVERED_BRIDGE_BODY=$(cat /tmp/edge_maint_recovery_bridge_ok.json)"
