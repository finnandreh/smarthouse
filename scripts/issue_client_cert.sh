#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <client-common-name> [--cn <subject-cn>] [--out-prefix <file-prefix>]"
  exit 1
fi

NAME="$1"
shift

SUBJECT_CN="${NAME}"
OUT_PREFIX="${NAME}"

while [ $# -gt 0 ]; do
  case "$1" in
    --cn)
      SUBJECT_CN="$2"
      shift 2
      ;;
    --out-prefix)
      OUT_PREFIX="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1"
      exit 1
      ;;
  esac
done

CERT_DIR="/mnt/c/smarthouse/certs"
CONF="${CERT_DIR}/openssl-ca.cnf"

if [ ! -f "${CONF}" ]; then
  echo "CA config not found. Run scripts/generate_mqtt_tls_certs.sh first."
  exit 1
fi

openssl genrsa -out "${CERT_DIR}/${OUT_PREFIX}.key" 2048
openssl req -new -key "${CERT_DIR}/${OUT_PREFIX}.key" -out "${CERT_DIR}/${OUT_PREFIX}.csr" -subj "/CN=${SUBJECT_CN}"
openssl ca -batch -config "${CONF}" -extensions client_ext -in "${CERT_DIR}/${OUT_PREFIX}.csr" -out "${CERT_DIR}/${OUT_PREFIX}.crt"
chmod 600 "${CERT_DIR}/${OUT_PREFIX}.key"
chmod 644 "${CERT_DIR}/${OUT_PREFIX}.crt"

echo "Issued client certificate: CN=${SUBJECT_CN}, prefix=${OUT_PREFIX}"
