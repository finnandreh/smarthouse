#!/usr/bin/env bash
set -euo pipefail

ROOT="/mnt/c/smarthouse"
BACKUPS="${ROOT}/certs-backups"

mkdir -p "${BACKUPS}"
# Ensure there is at least one backup directory to inflate.
if [ "$(find "${BACKUPS}" -mindepth 1 -maxdepth 1 -type d | wc -l)" -eq 0 ]; then
  mkdir -p "${BACKUPS}/00000000-000000"
fi

oldest="$(find "${BACKUPS}" -mindepth 1 -maxdepth 1 -type d | sort | sed -n '1p')"

dd if=/dev/zero of="${oldest}/size-test.bin" bs=1M count=3 status=none
before_kb="$(du -sk "${BACKUPS}" | awk '{print $1}')"
echo "BEFORE_TOTAL_KB=${before_kb}"

cd "${ROOT}"
BACKUP_RETENTION=100 BACKUP_MAX_MB=1 scripts/rotate_with_guardrails.sh | grep -E 'CERT_BACKUP|PRUNED_BACKUP_SIZE|PRUNED_BACKUP_COUNT|ROTATION_RESULT'

after_kb="$(du -sk "${BACKUPS}" | awk '{print $1}')"
count="$(find "${BACKUPS}" -mindepth 1 -maxdepth 1 -type d | wc -l)"
echo "AFTER_TOTAL_KB=${after_kb}"
echo "AFTER_COUNT=${count}"
