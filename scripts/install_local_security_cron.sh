#!/usr/bin/env bash
set -euo pipefail

ROOT="/mnt/c/smarthouse"
CRON_FILE="/tmp/smarthouse_cron.txt"

( crontab -l 2>/dev/null || true ) > "${CRON_FILE}"

grep -v 'smarthouse-security-check' "${CRON_FILE}" > "${CRON_FILE}.filtered" || true
mv "${CRON_FILE}.filtered" "${CRON_FILE}"

echo "0 2 * * * ${ROOT}/scripts/check_cert_expiry.sh >> ${ROOT}/logs/security-checks.log 2>&1 # smarthouse-security-check" >> "${CRON_FILE}"
echo "15 2 * * * ${ROOT}/scripts/check_mqtt_security_events.sh >> ${ROOT}/logs/security-checks.log 2>&1 # smarthouse-security-check" >> "${CRON_FILE}"
echo "30 2 * * * ${ROOT}/scripts/prune_revoked_tokens.sh >> ${ROOT}/logs/security-checks.log 2>&1 # smarthouse-security-check" >> "${CRON_FILE}"

mkdir -p "${ROOT}/logs"
crontab "${CRON_FILE}"

echo "Installed local security cron checks"
