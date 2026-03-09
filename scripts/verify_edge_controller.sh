#!/usr/bin/env bash
set -euo pipefail

EDGE_API_KEY="${EDGE_API_KEY:-changeme-edge-local-dev}"
EDGE_API_KEY_OPERATOR="${EDGE_API_KEY_OPERATOR:-changeme-edge-operator-local-dev}"
RUN_SUFFIX="$(date +%s%N)"

EDGE_DEVICE_ID="edge-device-${RUN_SUFFIX}"
EDGE_MAINT_BLOCK_ID="edge-maint-block-${RUN_SUFFIX}"
EDGE_SESSION_DEVICE_ID="edge-session-device-${RUN_SUFFIX}"
EDGE_OPERATOR_DEVICE_ID="edge-device-op-${RUN_SUFFIX}"
EDGE_IDEMP_DEVICE_ID="edge-idemp-device-${RUN_SUFFIX}"
EDGE_IDEMP_DEVICE_ID_CONFLICT="edge-idemp-device-conflict-${RUN_SUFFIX}"
EDGE_IDEMP_SESSION_DEVICE_ID="edge-idemp-session-device-${RUN_SUFFIX}"
IDEMP_KEY_PROVISION="edge-idem-provision-${RUN_SUFFIX}"
IDEMP_KEY_SESSION_PREPARE="edge-idem-session-prepare-${RUN_SUFFIX}"
IDEMP_KEY_SESSION_VALIDATE="edge-idem-session-validate-${RUN_SUFFIX}"
IDEMP_KEY_SESSION_ACTIVATE="edge-idem-session-activate-${RUN_SUFFIX}"

for i in $(seq 1 30); do
	if curl -fsS http://localhost:8084/health >/dev/null; then
		break
	fi
	sleep 2
done

for i in $(seq 1 30); do
	deps_check=$(curl -fsS http://localhost:8084/health/dependencies || true)
	if printf '%s' "${deps_check}" | grep -q '"status":"ok"'; then
		break
	fi
	sleep 2
done

edge_health=$(curl -fsS http://localhost:8084/health)
edge_deps=$(curl -fsS http://localhost:8084/health/dependencies)

edge_config_before=$(curl -fsS http://localhost:8084/config -H "x-edge-api-key: ${EDGE_API_KEY}")
edge_config_update=$(curl -fsS -X PUT http://localhost:8084/config -H "Content-Type: application/json" -H "x-edge-api-key: ${EDGE_API_KEY}" -d '{"site_id":"home01","site_name":"Primary Site","enabled_bridges":["modbus","knx","bacnet"]}')

edge_provision=$(curl -fsS -X POST http://localhost:8084/provision/device -H "Content-Type: application/json" -H "x-edge-api-key: ${EDGE_API_KEY}" -d '{"id":"'"${EDGE_DEVICE_ID}"'","house":"home01","type":"relay_module","protocol":"wifi","capabilities":["relay_output"]}')
edge_reload=$(curl -fsS -X POST http://localhost:8084/lifecycle/reload-automation -H "x-edge-api-key: ${EDGE_API_KEY}")
edge_bridges=$(curl -fsS -X POST http://localhost:8084/lifecycle/bridges/healthcheck -H "x-edge-api-key: ${EDGE_API_KEY}")
edge_bridge_reload=$(curl -fsS -X POST http://localhost:8084/lifecycle/bridges/modbus/reload -H "x-edge-api-key: ${EDGE_API_KEY}")
edge_bridge_restart=$(curl -fsS -X POST http://localhost:8084/lifecycle/bridges/knx/restart -H "x-edge-api-key: ${EDGE_API_KEY}")
edge_audit=$(curl -fsS http://localhost:8084/audit/recent -H "x-edge-api-key: ${EDGE_API_KEY}")

desired_before=$(curl -fsS http://localhost:8084/state/desired -H "x-edge-api-key: ${EDGE_API_KEY}")
desired_update=$(curl -fsS -X PUT http://localhost:8084/state/desired -H "Content-Type: application/json" -H "x-edge-api-key: ${EDGE_API_KEY}" -d '{"site_id":"home01","enabled_bridges":["modbus","knx","bacnet"],"automation_enabled":true,"provisioning_enabled":true}')
reconcile_run=$(curl -fsS -X POST http://localhost:8084/reconcile/run -H "x-edge-api-key: ${EDGE_API_KEY}")
reconcile_history=$(curl -fsS http://localhost:8084/reconcile/history -H "x-edge-api-key: ${EDGE_API_KEY}")
reconcile_metrics=$(curl -fsS "http://localhost:8084/metrics/reconcile?window_minutes=60" -H "x-edge-api-key: ${EDGE_API_KEY}")
reconcile_metrics_prom=$(curl -fsS "http://localhost:8084/metrics/reconcile/prometheus?window_minutes=60" -H "x-edge-api-key: ${EDGE_API_KEY}")

maintenance_enable=$(curl -fsS -X POST http://localhost:8084/maintenance/enable -H "Content-Type: application/json" -H "x-edge-api-key: ${EDGE_API_KEY}" -d '{"reason":"verify_maintenance"}')
code_bridge_command_during_maintenance=$(curl -s -o /tmp/edge_maintenance_bridge_cmd.json -w "%{http_code}" -X POST http://localhost:8084/lifecycle/bridges/bacnet/reload -H "x-edge-api-key: ${EDGE_API_KEY}")
code_provision_during_maintenance=$(curl -s -o /tmp/edge_maintenance_provision.json -w "%{http_code}" -X POST http://localhost:8084/provision/device -H "Content-Type: application/json" -H "x-edge-api-key: ${EDGE_API_KEY}" -d '{"id":"'"${EDGE_MAINT_BLOCK_ID}"'","house":"home01","type":"relay_module","protocol":"wifi","capabilities":["relay_output"]}')
maintenance_disable=$(curl -fsS -X POST http://localhost:8084/maintenance/disable -H "x-edge-api-key: ${EDGE_API_KEY}")

session_prepare=$(curl -fsS -X POST http://localhost:8084/provision/session/prepare -H "Content-Type: application/json" -H "x-edge-api-key: ${EDGE_API_KEY}" -d '{"id":"'"${EDGE_SESSION_DEVICE_ID}"'","house":"home01","type":"relay_module","protocol":"wifi","capabilities":["relay_output"],"installer_id":"edge-verify"}')
session_id=$(printf '%s' "${session_prepare}" | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
session_validate=$(curl -fsS -X POST "http://localhost:8084/provision/session/${session_id}/validate" -H "x-edge-api-key: ${EDGE_API_KEY}")
session_activate=$(curl -fsS -X POST "http://localhost:8084/provision/session/${session_id}/activate" -H "x-edge-api-key: ${EDGE_API_KEY}")
session_get=$(curl -fsS "http://localhost:8084/provision/session/${session_id}" -H "x-edge-api-key: ${EDGE_API_KEY}")

code_operator_reload=$(curl -s -o /tmp/edge_operator_reload.json -w "%{http_code}" -X POST http://localhost:8084/lifecycle/reload-automation -H "x-edge-api-key: ${EDGE_API_KEY_OPERATOR}")
code_operator_config_put=$(curl -s -o /tmp/edge_operator_config_put.json -w "%{http_code}" -X PUT http://localhost:8084/config -H "Content-Type: application/json" -H "x-edge-api-key: ${EDGE_API_KEY_OPERATOR}" -d '{"site_id":"home01","site_name":"Operator Attempt","enabled_bridges":["modbus","knx","bacnet"]}')
code_operator_config_get=$(curl -s -o /tmp/edge_operator_config_get.json -w "%{http_code}" -X GET http://localhost:8084/config -H "x-edge-api-key: ${EDGE_API_KEY_OPERATOR}")
code_operator_provision=$(curl -s -o /tmp/edge_operator_provision.json -w "%{http_code}" -X POST http://localhost:8084/provision/device -H "Content-Type: application/json" -H "x-edge-api-key: ${EDGE_API_KEY_OPERATOR}" -d '{"id":"'"${EDGE_OPERATOR_DEVICE_ID}"'","house":"home01","type":"relay_module","protocol":"wifi","capabilities":["relay_output"]}')
code_operator_bridge_command=$(curl -s -o /tmp/edge_operator_bridge_command.json -w "%{http_code}" -X POST http://localhost:8084/lifecycle/bridges/modbus/reload -H "x-edge-api-key: ${EDGE_API_KEY_OPERATOR}")

idem_provision_first=$(curl -fsS -X POST http://localhost:8084/provision/device -H "Content-Type: application/json" -H "x-edge-api-key: ${EDGE_API_KEY}" -H "Idempotency-Key: ${IDEMP_KEY_PROVISION}" -d '{"id":"'"${EDGE_IDEMP_DEVICE_ID}"'","house":"home01","type":"relay_module","protocol":"wifi","capabilities":["relay_output"]}')
idem_provision_second=$(curl -fsS -X POST http://localhost:8084/provision/device -H "Content-Type: application/json" -H "x-edge-api-key: ${EDGE_API_KEY}" -H "Idempotency-Key: ${IDEMP_KEY_PROVISION}" -d '{"id":"'"${EDGE_IDEMP_DEVICE_ID}"'","house":"home01","type":"relay_module","protocol":"wifi","capabilities":["relay_output"]}')
idem_provision_session_first=$(printf '%s' "${idem_provision_first}" | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
idem_provision_session_second=$(printf '%s' "${idem_provision_second}" | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
code_idem_provision_conflict=$(curl -s -o /tmp/edge_idem_provision_conflict.json -w "%{http_code}" -X POST http://localhost:8084/provision/device -H "Content-Type: application/json" -H "x-edge-api-key: ${EDGE_API_KEY}" -H "Idempotency-Key: ${IDEMP_KEY_PROVISION}" -d '{"id":"'"${EDGE_IDEMP_DEVICE_ID_CONFLICT}"'","house":"home01","type":"relay_module","protocol":"wifi","capabilities":["relay_output"]}')

idem_prepare_first=$(curl -fsS -X POST http://localhost:8084/provision/session/prepare -H "Content-Type: application/json" -H "x-edge-api-key: ${EDGE_API_KEY}" -H "Idempotency-Key: ${IDEMP_KEY_SESSION_PREPARE}" -d '{"id":"'"${EDGE_IDEMP_SESSION_DEVICE_ID}"'","house":"home01","type":"relay_module","protocol":"wifi","capabilities":["relay_output"],"installer_id":"edge-verify-idem"}')
idem_prepare_second=$(curl -fsS -X POST http://localhost:8084/provision/session/prepare -H "Content-Type: application/json" -H "x-edge-api-key: ${EDGE_API_KEY}" -H "Idempotency-Key: ${IDEMP_KEY_SESSION_PREPARE}" -d '{"id":"'"${EDGE_IDEMP_SESSION_DEVICE_ID}"'","house":"home01","type":"relay_module","protocol":"wifi","capabilities":["relay_output"],"installer_id":"edge-verify-idem"}')
idem_session_id=$(printf '%s' "${idem_prepare_first}" | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
idem_prepare_session_first=$(printf '%s' "${idem_prepare_first}" | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
idem_prepare_session_second=$(printf '%s' "${idem_prepare_second}" | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
idem_validate_first=$(curl -fsS -X POST "http://localhost:8084/provision/session/${idem_session_id}/validate" -H "x-edge-api-key: ${EDGE_API_KEY}" -H "Idempotency-Key: ${IDEMP_KEY_SESSION_VALIDATE}")
idem_validate_second=$(curl -fsS -X POST "http://localhost:8084/provision/session/${idem_session_id}/validate" -H "x-edge-api-key: ${EDGE_API_KEY}" -H "Idempotency-Key: ${IDEMP_KEY_SESSION_VALIDATE}")
idem_activate_first=$(curl -fsS -X POST "http://localhost:8084/provision/session/${idem_session_id}/activate" -H "x-edge-api-key: ${EDGE_API_KEY}" -H "Idempotency-Key: ${IDEMP_KEY_SESSION_ACTIVATE}")
idem_activate_second=$(curl -fsS -X POST "http://localhost:8084/provision/session/${idem_session_id}/activate" -H "x-edge-api-key: ${EDGE_API_KEY}" -H "Idempotency-Key: ${IDEMP_KEY_SESSION_ACTIVATE}")
idem_validate_first_canonical=$(printf '%s' "${idem_validate_first}" | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin), sort_keys=True))')
idem_validate_second_canonical=$(printf '%s' "${idem_validate_second}" | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin), sort_keys=True))')
idem_activate_first_canonical=$(printf '%s' "${idem_activate_first}" | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin), sort_keys=True))')
idem_activate_second_canonical=$(printf '%s' "${idem_activate_second}" | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin), sort_keys=True))')

if [ "${idem_provision_session_first}" != "${idem_provision_session_second}" ]; then
	echo "IDEMPOTENCY_PROVISION_SESSION_MISMATCH"
	exit 1
fi
if [ "${code_idem_provision_conflict}" != "409" ]; then
	echo "IDEMPOTENCY_PROVISION_CONFLICT_CODE_UNEXPECTED=${code_idem_provision_conflict}"
	exit 1
fi
if [ "${idem_prepare_session_first}" != "${idem_prepare_session_second}" ]; then
	echo "IDEMPOTENCY_SESSION_PREPARE_MISMATCH"
	exit 1
fi
if [ "${idem_validate_first_canonical}" != "${idem_validate_second_canonical}" ]; then
	echo "IDEMPOTENCY_SESSION_VALIDATE_MISMATCH"
	exit 1
fi
if [ "${idem_activate_first_canonical}" != "${idem_activate_second_canonical}" ]; then
	echo "IDEMPOTENCY_SESSION_ACTIVATE_MISMATCH"
	exit 1
fi

if ! printf '%s' "${reconcile_metrics}" | grep -q '"total_events"'; then
	echo "RECONCILE_METRICS_MISSING_TOTAL_EVENTS"
	exit 1
fi
if ! printf '%s' "${reconcile_metrics}" | grep -q '"alerts"'; then
	echo "RECONCILE_METRICS_MISSING_ALERTS"
	exit 1
fi
if ! printf '%s' "${reconcile_metrics_prom}" | grep -q 'edge_reconcile_total_events'; then
	echo "RECONCILE_PROM_METRICS_MISSING_TOTAL_EVENTS"
	exit 1
fi
if ! printf '%s' "${reconcile_metrics_prom}" | grep -q 'edge_reconcile_slo_violation'; then
	echo "RECONCILE_PROM_METRICS_MISSING_SLO_VIOLATION"
	exit 1
fi

echo "EDGE_HEALTH=${edge_health}"
echo "EDGE_DEPS=${edge_deps}"
echo "EDGE_RUN_SUFFIX=${RUN_SUFFIX}"
echo "EDGE_DEVICE_ID=${EDGE_DEVICE_ID}"
echo "EDGE_MAINT_BLOCK_ID=${EDGE_MAINT_BLOCK_ID}"
echo "EDGE_SESSION_DEVICE_ID=${EDGE_SESSION_DEVICE_ID}"
echo "EDGE_OPERATOR_DEVICE_ID=${EDGE_OPERATOR_DEVICE_ID}"
echo "EDGE_CONFIG_BEFORE=${edge_config_before}"
echo "EDGE_CONFIG_UPDATE=${edge_config_update}"
echo "EDGE_PROVISION=${edge_provision}"
echo "EDGE_RELOAD=${edge_reload}"
echo "EDGE_BRIDGES=${edge_bridges}"
echo "EDGE_BRIDGE_RELOAD=${edge_bridge_reload}"
echo "EDGE_BRIDGE_RESTART=${edge_bridge_restart}"
echo "EDGE_AUDIT=${edge_audit}"
echo "EDGE_DESIRED_BEFORE=${desired_before}"
echo "EDGE_DESIRED_UPDATE=${desired_update}"
echo "EDGE_RECONCILE_RUN=${reconcile_run}"
echo "EDGE_RECONCILE_HISTORY=${reconcile_history}"
echo "EDGE_RECONCILE_METRICS=${reconcile_metrics}"
echo "EDGE_RECONCILE_METRICS_PROM=${reconcile_metrics_prom}"
echo "EDGE_MAINTENANCE_ENABLE=${maintenance_enable}"
echo "EDGE_MAINTENANCE_DISABLE=${maintenance_disable}"
echo "EDGE_BRIDGE_COMMAND_DURING_MAINTENANCE_CODE=${code_bridge_command_during_maintenance}"
echo "EDGE_BRIDGE_COMMAND_DURING_MAINTENANCE_BODY=$(cat /tmp/edge_maintenance_bridge_cmd.json)"
echo "EDGE_PROVISION_DURING_MAINTENANCE_CODE=${code_provision_during_maintenance}"
echo "EDGE_PROVISION_DURING_MAINTENANCE_BODY=$(cat /tmp/edge_maintenance_provision.json)"
echo "EDGE_SESSION_PREPARE=${session_prepare}"
echo "EDGE_SESSION_VALIDATE=${session_validate}"
echo "EDGE_SESSION_ACTIVATE=${session_activate}"
echo "EDGE_SESSION_GET=${session_get}"
echo "EDGE_OPERATOR_RELOAD_CODE=${code_operator_reload}"
echo "EDGE_OPERATOR_CONFIG_PUT_CODE=${code_operator_config_put}"
echo "EDGE_OPERATOR_CONFIG_GET_CODE=${code_operator_config_get}"
echo "EDGE_OPERATOR_PROVISION_CODE=${code_operator_provision}"
echo "EDGE_OPERATOR_BRIDGE_COMMAND_CODE=${code_operator_bridge_command}"
echo "EDGE_OPERATOR_RELOAD_BODY=$(cat /tmp/edge_operator_reload.json)"
echo "EDGE_OPERATOR_CONFIG_PUT_BODY=$(cat /tmp/edge_operator_config_put.json)"
echo "EDGE_OPERATOR_CONFIG_GET_BODY=$(cat /tmp/edge_operator_config_get.json)"
echo "EDGE_OPERATOR_PROVISION_BODY=$(cat /tmp/edge_operator_provision.json)"
echo "EDGE_OPERATOR_BRIDGE_COMMAND_BODY=$(cat /tmp/edge_operator_bridge_command.json)"
echo "EDGE_IDEMP_KEY_PROVISION=${IDEMP_KEY_PROVISION}"
echo "EDGE_IDEMP_PROVISION_FIRST=${idem_provision_first}"
echo "EDGE_IDEMP_PROVISION_SECOND=${idem_provision_second}"
echo "EDGE_IDEMP_PROVISION_CONFLICT_CODE=${code_idem_provision_conflict}"
echo "EDGE_IDEMP_PROVISION_CONFLICT_BODY=$(cat /tmp/edge_idem_provision_conflict.json)"
echo "EDGE_IDEMP_KEY_SESSION_PREPARE=${IDEMP_KEY_SESSION_PREPARE}"
echo "EDGE_IDEMP_SESSION_PREPARE_FIRST=${idem_prepare_first}"
echo "EDGE_IDEMP_SESSION_PREPARE_SECOND=${idem_prepare_second}"
echo "EDGE_IDEMP_KEY_SESSION_VALIDATE=${IDEMP_KEY_SESSION_VALIDATE}"
echo "EDGE_IDEMP_SESSION_VALIDATE_FIRST=${idem_validate_first}"
echo "EDGE_IDEMP_SESSION_VALIDATE_SECOND=${idem_validate_second}"
echo "EDGE_IDEMP_KEY_SESSION_ACTIVATE=${IDEMP_KEY_SESSION_ACTIVATE}"
echo "EDGE_IDEMP_SESSION_ACTIVATE_FIRST=${idem_activate_first}"
echo "EDGE_IDEMP_SESSION_ACTIVATE_SECOND=${idem_activate_second}"
