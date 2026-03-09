#!/usr/bin/env bash
set -euo pipefail

CERT_DIR="/mnt/c/smarthouse/certs"
WARN_DAYS="${WARN_DAYS:-30}"
WARN_SECONDS=$((WARN_DAYS * 86400))

status=0
for crt in "${CERT_DIR}"/*.crt; do
  [ -f "$crt" ] || continue
  if openssl x509 -checkend "${WARN_SECONDS}" -noout -in "$crt" >/dev/null; then
    echo "CERT_OK=$(basename "$crt")"
  else
    echo "CERT_EXPIRING_SOON=$(basename "$crt")"
    status=1
  fi
done

exit "$status"
