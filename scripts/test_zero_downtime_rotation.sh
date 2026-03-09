#!/usr/bin/env bash
set -euo pipefail

cd /mnt/c/smarthouse

out="$(scripts/rotate_service_zero_downtime.sh device-registry)"
echo "$out"

prev="$(printf '%s' "$out" | awk -F= '/^PREV_CERT=/{print $2}')"
if [ -z "$prev" ]; then
  echo "FAILED_TO_PARSE_PREV_CERT"
  exit 1
fi

scripts/finalize_zero_downtime_rotation.sh device-registry "$prev"
