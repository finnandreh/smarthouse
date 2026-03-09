#!/usr/bin/env bash
set -euo pipefail

cd /mnt/c/smarthouse

PYTHON_BIN="python3"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "python3 not found"
  exit 1
fi

REGISTRY_URL="${DEVICE_REGISTRY_URL:-http://localhost:8081}"
PROVISIONING_KEY="${PROVISIONING_MASTER_KEY:-changeme-provisioning-local-dev}"
RUN_SUFFIX="$(date +%s%N)"
DEVICE_ID="sdk-bootstrap-${RUN_SUFFIX}"
SUBJECT="sdk-bootstrap-${RUN_SUFFIX}"

BOOTSTRAP_OUTPUT=$(
  "${PYTHON_BIN}" -m device_sdk.examples.bootstrap_register \
    --registry-url "${REGISTRY_URL}" \
    --provisioning-key "${PROVISIONING_KEY}" \
    --subject "${SUBJECT}" \
    --house "home01" \
    --device-id "${DEVICE_ID}" \
    --device-type "relay_module" \
    --protocol "wifi" \
    --capabilities "relay_output" \
    --token-role "provisioner" \
    --token-scopes "device:register" \
    --token-expires-minutes 15 \
    --require-lookup
)

echo "DEVICE_SDK_BOOTSTRAP_OUTPUT=${BOOTSTRAP_OUTPUT}"
echo "DEVICE_SDK_BOOTSTRAP_TOKEN=passed"
echo "DEVICE_SDK_BOOTSTRAP_REGISTER=passed"
echo "DEVICE_SDK_BOOTSTRAP_LOOKUP=passed"

echo "VERIFY_DEVICE_SDK_BOOTSTRAP=passed"
