#!/usr/bin/env bash
set -euo pipefail

PROVISIONING_MASTER_KEY="${PROVISIONING_MASTER_KEY:-changeme-provisioning-local-dev}"
RUN_SUFFIX="$(date +%s%N)"
REGISTER_DEVICE_ID="revoked-test-${RUN_SUFFIX}"

register_payload='{"id":"'"${REGISTER_DEVICE_ID}"'","house":"home01","type":"relay_module","protocol":"wifi","capabilities":["relay_output"]}'

admin_token=$(PROVISIONING_MASTER_KEY="${PROVISIONING_MASTER_KEY}" scripts/auth_token.sh verify-auth-admin admin home01 rules:reload 30)
operator_token=$(PROVISIONING_MASTER_KEY="${PROVISIONING_MASTER_KEY}" scripts/auth_token.sh verify-auth-operator operator home01 device:register 30)

code_pre_revoke=$(curl -s -o /tmp/reg_before_revoke.json -w "%{http_code}" -X POST http://localhost:8081/devices/register -H "Content-Type: application/json" -H "Authorization: Bearer ${operator_token}" -d "${register_payload}")

code_revoke=$(curl -s -o /tmp/revoke_response.json -w "%{http_code}" -X POST http://localhost:8081/auth/revoke -H "Content-Type: application/json" -H "Authorization: Bearer ${admin_token}" -d "{\"token\":\"${operator_token}\"}")

code_post_revoke_reg=$(curl -s -o /tmp/reg_after_revoke.json -w "%{http_code}" -X POST http://localhost:8081/devices/register -H "Content-Type: application/json" -H "Authorization: Bearer ${operator_token}" -d "${register_payload}")
code_post_revoke_reload=$(curl -s -o /tmp/reload_after_revoke.json -w "%{http_code}" -X POST http://localhost:8082/rules/reload -H "Authorization: Bearer ${operator_token}")

echo "PRE_REVOKE_REGISTER_CODE=${code_pre_revoke}"
echo "REVOKE_CODE=${code_revoke}"
echo "POST_REVOKE_REGISTER_CODE=${code_post_revoke_reg}"
echo "POST_REVOKE_RELOAD_CODE=${code_post_revoke_reload}"
echo "REGISTER_DEVICE_ID=${REGISTER_DEVICE_ID}"
echo "PRE_REVOKE_REGISTER_BODY=$(cat /tmp/reg_before_revoke.json)"
echo "REVOKE_BODY=$(cat /tmp/revoke_response.json)"
echo "POST_REVOKE_REGISTER_BODY=$(cat /tmp/reg_after_revoke.json)"
echo "POST_REVOKE_RELOAD_BODY=$(cat /tmp/reload_after_revoke.json)"
