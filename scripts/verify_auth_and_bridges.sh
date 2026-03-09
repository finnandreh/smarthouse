#!/usr/bin/env bash
set -euo pipefail

PROVISIONING_MASTER_KEY="${PROVISIONING_MASTER_KEY:-changeme-provisioning-local-dev}"

register_payload='{"id":"auth-test","house":"home01","type":"relay_module","protocol":"wifi","capabilities":["relay_output"]}'

register_token=$(PROVISIONING_MASTER_KEY="${PROVISIONING_MASTER_KEY}" scripts/auth_token.sh verify-auth-register operator home01 device:register 30)
reload_token=$(PROVISIONING_MASTER_KEY="${PROVISIONING_MASTER_KEY}" scripts/auth_token.sh verify-auth-reload admin home01 rules:reload 30)
bad_scope_token=$(PROVISIONING_MASTER_KEY="${PROVISIONING_MASTER_KEY}" scripts/auth_token.sh verify-auth-bad-scope automation-admin home01 rules:reload 30)
bad_role_token=$(PROVISIONING_MASTER_KEY="${PROVISIONING_MASTER_KEY}" scripts/auth_token.sh verify-auth-bad-role operator home01 device:register 30)

code_unauth_reg=$(curl -s -o /tmp/reg_unauth.json -w "%{http_code}" -X POST http://localhost:8081/devices/register -H "Content-Type: application/json" -d "$register_payload")
code_auth_reg=$(curl -s -o /tmp/reg_auth.json -w "%{http_code}" -X POST http://localhost:8081/devices/register -H "Content-Type: application/json" -H "Authorization: Bearer ${register_token}" -d "$register_payload")

code_unauth_reload=$(curl -s -o /tmp/reload_unauth.json -w "%{http_code}" -X POST http://localhost:8082/rules/reload)
code_auth_reload=$(curl -s -o /tmp/reload_auth.json -w "%{http_code}" -X POST http://localhost:8082/rules/reload -H "Authorization: Bearer ${reload_token}")
code_forbidden_scope_reg=$(curl -s -o /tmp/reg_forbidden_scope.json -w "%{http_code}" -X POST http://localhost:8081/devices/register -H "Content-Type: application/json" -H "Authorization: Bearer ${bad_scope_token}" -d "$register_payload")
code_forbidden_role_reload=$(curl -s -o /tmp/reload_forbidden_role.json -w "%{http_code}" -X POST http://localhost:8082/rules/reload -H "Authorization: Bearer ${bad_role_token}")

bridge_modbus_health=$(curl -fsS http://localhost:8091/health)
bridge_knx_health=$(curl -fsS http://localhost:8092/health)
bridge_bacnet_health=$(curl -fsS http://localhost:8093/health)

bridge_emit_modbus=$(curl -fsS -X POST http://localhost:8091/emit-test -H "Content-Type: application/json" -d '{"event":"register_read","value":230.1}')
bridge_emit_knx=$(curl -fsS -X POST http://localhost:8092/emit-test -H "Content-Type: application/json" -d '{"event":"group_write","value":1}')
bridge_emit_bacnet=$(curl -fsS -X POST http://localhost:8093/emit-test -H "Content-Type: application/json" -d '{"event":"analog_input","value":22.8}')

echo "REG_UNAUTH_CODE=${code_unauth_reg}"
echo "REG_AUTH_CODE=${code_auth_reg}"
echo "RELOAD_UNAUTH_CODE=${code_unauth_reload}"
echo "RELOAD_AUTH_CODE=${code_auth_reload}"
echo "REG_FORBIDDEN_SCOPE_CODE=${code_forbidden_scope_reg}"
echo "RELOAD_FORBIDDEN_ROLE_CODE=${code_forbidden_role_reload}"
echo "REG_UNAUTH_BODY=$(cat /tmp/reg_unauth.json)"
echo "REG_AUTH_BODY=$(cat /tmp/reg_auth.json)"
echo "RELOAD_UNAUTH_BODY=$(cat /tmp/reload_unauth.json)"
echo "RELOAD_AUTH_BODY=$(cat /tmp/reload_auth.json)"
echo "REG_FORBIDDEN_SCOPE_BODY=$(cat /tmp/reg_forbidden_scope.json)"
echo "RELOAD_FORBIDDEN_ROLE_BODY=$(cat /tmp/reload_forbidden_role.json)"
echo "BRIDGE_MODBUS_HEALTH=${bridge_modbus_health}"
echo "BRIDGE_KNX_HEALTH=${bridge_knx_health}"
echo "BRIDGE_BACNET_HEALTH=${bridge_bacnet_health}"
echo "BRIDGE_MODBUS_EMIT=${bridge_emit_modbus}"
echo "BRIDGE_KNX_EMIT=${bridge_emit_knx}"
echo "BRIDGE_BACNET_EMIT=${bridge_emit_bacnet}"
