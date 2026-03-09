#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <client-common-name>|--cert <path-to-cert>"
  exit 1
fi

CERT_DIR="/mnt/c/smarthouse/certs"
CONF="${CERT_DIR}/openssl-ca.cnf"

if [ "$1" = "--cert" ]; then
  CRT="$2"
  NAME="$(basename "${CRT}" .crt)"
else
  NAME="$1"
  CRT="${CERT_DIR}/${NAME}.crt"
fi

if [ ! -f "${CRT}" ]; then
  echo "Certificate not found: ${CRT}"
  exit 1
fi

openssl ca -config "${CONF}" -revoke "${CRT}"
openssl ca -gencrl -config "${CONF}" -out "${CERT_DIR}/ca.crl"

echo "Revoked certificate for ${NAME} and regenerated CRL"
