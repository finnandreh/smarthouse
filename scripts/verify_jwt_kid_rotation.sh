#!/usr/bin/env bash
set -euo pipefail

PROVISIONING_MASTER_KEY="${PROVISIONING_MASTER_KEY:-changeme-provisioning-local-dev}"
JWT_SECRET="${JWT_SECRET:-smarthouse-jwt-local-dev-secret}"
JWT_PREVIOUS_SECRET="${JWT_PREVIOUS_SECRET:-smarthouse-jwt-previous-local-dev-secret}"
JWT_ISSUER="${JWT_ISSUER:-smarthouse-device-registry}"
JWT_AUDIENCE="${JWT_AUDIENCE:-smarthouse-services}"
JWT_ACTIVE_KID="${JWT_ACTIVE_KID:-k1}"
JWT_PREVIOUS_KID="${JWT_PREVIOUS_KID:-k0}"
RUN_SUFFIX="$(date +%s%N)"

ACTIVE_DEVICE_ID="kid-active-${RUN_SUFFIX}"
PREVIOUS_DEVICE_ID="kid-prev-${RUN_SUFFIX}"
UNKNOWN_DEVICE_ID="kid-unknown-${RUN_SUFFIX}"

active_token=$(PROVISIONING_MASTER_KEY="${PROVISIONING_MASTER_KEY}" scripts/auth_token.sh verify-kid-active operator home01 device:register 30)

active_register_payload='{"id":"'"${ACTIVE_DEVICE_ID}"'","house":"home01","type":"relay_module","protocol":"wifi","capabilities":["relay_output"]}'
previous_register_payload='{"id":"'"${PREVIOUS_DEVICE_ID}"'","house":"home01","type":"relay_module","protocol":"wifi","capabilities":["relay_output"]}'
unknown_register_payload='{"id":"'"${UNKNOWN_DEVICE_ID}"'","house":"home01","type":"relay_module","protocol":"wifi","capabilities":["relay_output"]}'

active_header_json=$(python3 -c 'import base64,json,sys; h=sys.argv[1].split(".")[0]; h += "=" * (-len(h) % 4); print(base64.urlsafe_b64decode(h.encode()).decode())' "${active_token}")
active_kid=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("kid",""))' "${active_header_json}")

previous_token=$(docker exec smarthouse-device-registry python -c "import datetime,jwt,time,uuid; now=int(time.time()); payload={'sub':'verify-kid-prev','role':'operator','house':'home01','scopes':['device:register'],'iss':'${JWT_ISSUER}','aud':'${JWT_AUDIENCE}','iat':now,'exp':now+1800,'jti':str(uuid.uuid4())}; print(jwt.encode(payload, '${JWT_PREVIOUS_SECRET}', algorithm='HS256', headers={'kid':'${JWT_PREVIOUS_KID}'}))")
unknown_kid_token=$(docker exec smarthouse-device-registry python -c "import datetime,jwt,time,uuid; now=int(time.time()); payload={'sub':'verify-kid-unknown','role':'operator','house':'home01','scopes':['device:register'],'iss':'${JWT_ISSUER}','aud':'${JWT_AUDIENCE}','iat':now,'exp':now+1800,'jti':str(uuid.uuid4())}; print(jwt.encode(payload, '${JWT_SECRET}', algorithm='HS256', headers={'kid':'unknown-kid'}))")

code_active=$(curl -s -o /tmp/kid_active_reg.json -w "%{http_code}" -X POST http://localhost:8081/devices/register -H "Content-Type: application/json" -H "Authorization: Bearer ${active_token}" -d "${active_register_payload}")
code_previous=$(curl -s -o /tmp/kid_previous_reg.json -w "%{http_code}" -X POST http://localhost:8081/devices/register -H "Content-Type: application/json" -H "Authorization: Bearer ${previous_token}" -d "${previous_register_payload}")
code_unknown=$(curl -s -o /tmp/kid_unknown_reg.json -w "%{http_code}" -X POST http://localhost:8081/devices/register -H "Content-Type: application/json" -H "Authorization: Bearer ${unknown_kid_token}" -d "${unknown_register_payload}")

echo "ACTIVE_KID=${active_kid}"
echo "KID_ROTATION_RUN_SUFFIX=${RUN_SUFFIX}"
echo "KID_ACTIVE_DEVICE_ID=${ACTIVE_DEVICE_ID}"
echo "KID_PREVIOUS_DEVICE_ID=${PREVIOUS_DEVICE_ID}"
echo "KID_UNKNOWN_DEVICE_ID=${UNKNOWN_DEVICE_ID}"
echo "ACTIVE_TOKEN_REGISTER_CODE=${code_active}"
echo "PREVIOUS_KID_TOKEN_REGISTER_CODE=${code_previous}"
echo "UNKNOWN_KID_TOKEN_REGISTER_CODE=${code_unknown}"
echo "ACTIVE_REGISTER_BODY=$(cat /tmp/kid_active_reg.json)"
echo "PREVIOUS_REGISTER_BODY=$(cat /tmp/kid_previous_reg.json)"
echo "UNKNOWN_REGISTER_BODY=$(cat /tmp/kid_unknown_reg.json)"
