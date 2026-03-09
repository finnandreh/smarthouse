#!/usr/bin/env bash
set -euo pipefail

cd /mnt/c/smarthouse

PYTHON_BIN="python3"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "python3 not found"
  exit 1
fi

"${PYTHON_BIN}" -m unittest discover -s tests/device_sdk -p "test_*.py" -v

echo "VERIFY_DEVICE_SDK_UNIT=passed"
