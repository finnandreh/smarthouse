# VS Code Exact Setup

Use this guide to match the project development environment as closely as possible.

## 0. Prerequisites

- Windows Python launcher (`py`) installed.
- Python `3.12.x` installed (required for `psycopg[binary]==3.2.1` on this project stack).
- If you already have `.venv` created with another Python version, remove it first:

```powershell
Remove-Item -Recurse -Force C:\smarthouse\.venv
```

## 1. Open Workspace

- Open folder: `C:\smarthouse`
- If prompted, install recommended extensions from `.vscode/extensions.json`.

## 2. Create/Refresh Local Python venv

### From Windows PowerShell

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_local_dev_venv.ps1 -Root C:\smarthouse
```

Optional explicit version flag:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_local_dev_venv.ps1 -Root C:\smarthouse -PythonVersion 3.12
```

### From WSL

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && chmod +x scripts/setup_local_dev_venv.sh && scripts/setup_local_dev_venv.sh /mnt/c/smarthouse"
```

If Python 3.12 is not available as `python3.12`, pass an explicit binary:

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && PYTHON_BIN=/usr/bin/python3.12 scripts/setup_local_dev_venv.sh /mnt/c/smarthouse"
```

## 3. VS Code Python Interpreter

Select interpreter:

- `C:\smarthouse\.venv\Scripts\python.exe`

Workspace defaults are preconfigured in `.vscode/settings.json`.

## 4. Validate the Exact Setup

Run these commands:

```powershell
C:/smarthouse/.venv/Scripts/python.exe -m unittest tests.system.test_house_designer_contracts -v
C:/smarthouse/.venv/Scripts/python.exe scripts/generate_parts_list.py --input examples/house_designer/client_demo.json --output C:/smarthouse/logs/parts_demo.json
```

Expected:

- tests pass
- `PARTS_GENERATION=ok ...`
- setup command ends with `SETUP_VENV=ok ... python=3.12`

## 5. Runtime Stack Context

For runtime services and integration tests, use WSL terminal commands:

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && docker compose up -d --build"
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && scripts/verify_system_tests.sh"
```

This keeps the same separation used in this project:

- VS Code + `.venv` for local scripts and contract tooling
- WSL + Docker for service runtime validation
