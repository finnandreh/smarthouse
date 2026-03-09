#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/mnt/c/smarthouse"
CERT_DIR="${ROOT_DIR}/certs"
BACKUP_ROOT="${ROOT_DIR}/certs-backups"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="${BACKUP_ROOT}/${TIMESTAMP}"
BACKUP_RETENTION="${BACKUP_RETENTION:-14}"
BACKUP_MAX_MB="${BACKUP_MAX_MB:-0}"

mkdir -p "${BACKUP_ROOT}"
cp -a "${CERT_DIR}" "${BACKUP_DIR}"

echo "CERT_BACKUP=${BACKUP_DIR}"

prune_backups() {
  if ! [[ "${BACKUP_RETENTION}" =~ ^[0-9]+$ ]]; then
    echo "Invalid BACKUP_RETENTION value: ${BACKUP_RETENTION}"
    return 1
  fi

  mapfile -t backups < <(find "${BACKUP_ROOT}" -mindepth 1 -maxdepth 1 -type d | sort)
  backup_count="${#backups[@]}"

  if [ "${backup_count}" -le "${BACKUP_RETENTION}" ]; then
    :
  else
    to_delete=$((backup_count - BACKUP_RETENTION))
    for ((i=0; i<to_delete; i++)); do
      rm -rf "${backups[$i]}"
      echo "PRUNED_BACKUP_COUNT=${backups[$i]}"
    done
  fi

  if ! [[ "${BACKUP_MAX_MB}" =~ ^[0-9]+$ ]]; then
    echo "Invalid BACKUP_MAX_MB value: ${BACKUP_MAX_MB}"
    return 1
  fi

  if [ "${BACKUP_MAX_MB}" -eq 0 ]; then
    return 0
  fi

  max_kb=$((BACKUP_MAX_MB * 1024))
  while true; do
    mapfile -t backups < <(find "${BACKUP_ROOT}" -mindepth 1 -maxdepth 1 -type d | sort)
    if [ "${#backups[@]}" -eq 0 ]; then
      break
    fi

    total_kb=$(du -sk "${BACKUP_ROOT}" | awk '{print $1}')
    if [ "${total_kb}" -le "${max_kb}" ]; then
      break
    fi

    rm -rf "${backups[0]}"
    echo "PRUNED_BACKUP_SIZE=${backups[0]}"
  done
}

post_rotate_checks() {
  "${ROOT_DIR}/scripts/verify_mqtt_auth.sh"
  "${ROOT_DIR}/scripts/verify_acl_enforcement.sh"
  "${ROOT_DIR}/scripts/verify_plaintext_disabled.sh"
  "${ROOT_DIR}/scripts/smoke_test_e2e.sh"
}

rollback() {
  echo "ROTATION_RESULT=failed_rolling_back"
  rm -rf "${CERT_DIR}"
  cp -a "${BACKUP_DIR}/certs" "${CERT_DIR}"
  docker compose -f "${ROOT_DIR}/docker-compose.yml" restart mqtt device-registry automation-engine bridge-modbus bridge-knx bridge-bacnet
}

cd "${ROOT_DIR}"

if ! SKIP_RESTART=true "${ROOT_DIR}/scripts/rotate_service_certs.sh"; then
  rollback
  exit 1
fi

docker compose -f "${ROOT_DIR}/docker-compose.yml" restart mqtt device-registry automation-engine bridge-modbus bridge-knx bridge-bacnet

if ! post_rotate_checks; then
  rollback
  echo "ROTATION_RESULT=rollback_completed"
  exit 1
fi

prune_backups

echo "ROTATION_RESULT=success"
