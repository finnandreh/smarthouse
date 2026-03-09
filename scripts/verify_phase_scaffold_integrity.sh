#!/usr/bin/env bash
set -euo pipefail

cd /mnt/c/smarthouse

required_paths=(
  "services/project_engine/app/main.py"
  "services/system_generator/README.md"
  "installer_platform/README.md"
  "cloud_services/README.md"
  "services/telemetry/README.md"
  "services/ai/README.md"
  "tests/system/README.md"
  "monitoring/README.md"
  "docs/PHASE_SCAFFOLD_STATUS.md"
)

for p in "${required_paths[@]}"; do
  if [[ ! -f "${p}" ]]; then
    echo "Missing scaffold artifact: ${p}"
    exit 1
  fi
  if [[ ! -s "${p}" ]]; then
    echo "Scaffold artifact is empty: ${p}"
    exit 1
  fi
  echo "SCAFFOLD_PATH_OK=${p}"
done

if ! grep -q "project-engine" docker-compose.yml; then
  echo "docker-compose.yml missing project-engine service"
  exit 1
fi

if ! grep -q "PHASE_SCAFFOLD_STATUS.md" docs/DOCUMENTATION_INDEX.md; then
  echo "docs/DOCUMENTATION_INDEX.md missing scaffold status reference"
  exit 1
fi

echo "VERIFY_PHASE_SCAFFOLD_INTEGRITY=passed"
