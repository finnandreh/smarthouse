#!/usr/bin/env bash
set -euo pipefail

cd /mnt/c/smarthouse
python3 -m unittest discover -s tests/system -p 'test_*.py' -v

echo "VERIFY_SYSTEM_TESTS=passed"
