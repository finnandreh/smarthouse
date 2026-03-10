#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-/mnt/c/smarthouse}"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"
if [[ ! -d "${ROOT}" ]]; then
  echo "SETUP_VENV=failed reason=missing_root path=${ROOT}"
  exit 1
fi

cd "${ROOT}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "SETUP_VENV=failed reason=missing_python python=${PYTHON_BIN}"
  echo "Hint: install Python 3.12 or run with PYTHON_BIN set to a Python 3.12 executable."
  exit 1
fi

if [[ ! -d ".venv" ]]; then
  "${PYTHON_BIN}" -m venv .venv
fi

if [[ ! -x "./.venv/bin/python" ]]; then
  echo "SETUP_VENV=failed reason=missing_interpreter path=${ROOT}/.venv/bin/python"
  exit 1
fi

actual_version="$(./.venv/bin/python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if [[ "${actual_version}" != "3.12" ]]; then
  echo "SETUP_VENV=failed reason=python_version_mismatch expected=3.12 actual=${actual_version}"
  echo "Hint: remove .venv and rerun with Python 3.12."
  exit 1
fi

./.venv/bin/python -m pip install --upgrade pip

while IFS= read -r req; do
  [[ -f "${req}" ]] || continue
  echo "Installing ${req}"
  ./.venv/bin/python -m pip install -r "${req}"
done < <(find . -name requirements.txt -not -path "./.venv/*" | sort)

echo "SETUP_VENV=ok interpreter=${ROOT}/.venv/bin/python python=${actual_version}"
