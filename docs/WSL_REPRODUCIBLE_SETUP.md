# WSL Reproducible Setup Guide

Use this guide to reproduce the same SmartHouse development environment on a new machine or from a fresh GitHub clone.

For exact VS Code + `.venv` alignment, also follow:

- `docs/VS_CODE_EXACT_SETUP.md`

## Goal

Create a WSL distro dedicated to SmartHouse development (`smarthouse-dev`) with Docker and workspace access that matches this project's expected workflow.

## 1. Host Prerequisites (Windows)

1. Install WSL (PowerShell as Administrator):

```powershell
wsl --install
```

2. Install Docker Desktop and enable:
- WSL 2 based engine
- Integration with the distro you will use (`smarthouse-dev`)

3. Verify host tools:

```powershell
wsl --status
docker --version
```

If `docker` is not available in Windows PATH, Docker can still work inside WSL as long as Docker Desktop WSL integration is enabled.

## 2. Create/Prepare `smarthouse-dev` Distro

Important safety rule:

- Do not modify your existing daily-use distro directly for this project.
- Always create a dedicated fresh distro (`smarthouse-dev`) or a cloned copy with a new name.

First inspect existing distros:

```powershell
wsl -l -v
```

Option A: Create fresh distro for SmartHouse.

```powershell
wsl --install -d Ubuntu
```

Then open it once, create username/password, and use it only for SmartHouse.

Option B: Clone existing distro to a fresh named copy (recommended when you already have working WSL distros).

1. Export existing source distro:

```powershell
wsl --export <source-distro> C:\temp\<source-distro>.tar
```

2. Import as dedicated SmartHouse distro:

```powershell
wsl --import smarthouse-dev C:\WSL\smarthouse-dev C:\temp\<source-distro>.tar --version 2
```

3. Open the new distro and finalize user setup if needed.

4. Enable Docker Desktop WSL integration for `smarthouse-dev` only.

This guarantees a clean copy with separate name/config and avoids interfering with existing WSL environments.

Option C: If `smarthouse-dev` already exists but is dirty, recreate from clean export/import.

```powershell
wsl --unregister smarthouse-dev
wsl --import smarthouse-dev C:\WSL\smarthouse-dev C:\temp\<baseline>.tar --version 2
```

Warning: `--unregister` deletes that distro data permanently. Use only for disposable/reproducible copies.

## 3. Base Packages Inside WSL

Run inside WSL:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git jq python3 python3-pip python3-venv
```

## 4. Clone and Open Project

From Windows PowerShell:

```powershell
git clone <repo-url> C:\smarthouse
```

If cloned elsewhere, replace paths in commands accordingly.

Open VS Code on the workspace and use WSL terminal context for runtime commands.

## 5. Verify Docker Access From WSL

Inside WSL:

```bash
docker --version
docker compose version
```

If these fail:
- Open Docker Desktop Settings -> Resources -> WSL Integration
- Enable integration for your distro
- Restart Docker Desktop

## 6. First Project Bring-Up

Inside WSL:

```bash
cd /mnt/c/smarthouse
chmod +x scripts/generate_mqtt_tls_certs.sh
scripts/generate_mqtt_tls_certs.sh

docker compose up -d --build
```

Then verify:

```bash
chmod +x scripts/verify_system_tests.sh
scripts/verify_system_tests.sh
```

Expected result includes:

- `VERIFY_SYSTEM_TESTS=passed`

## 7. Design Workflow Entry

Once platform is up:

1. Open `web/house_designer/index.html` in browser.
2. Export JSON design.
3. Run parts generation:

```bash
cd /mnt/c/smarthouse
C:/smarthouse/.venv/Scripts/python.exe scripts/generate_parts_list.py --input examples/house_designer/client_demo.json --output C:/smarthouse/logs/parts_demo.json
```

## 8. Portable/Repeatable Team Baseline

For team consistency, standardize on:

- WSL distro name: `smarthouse-dev`
- Workspace path: `C:\smarthouse`
- Core verification command: `scripts/verify_system_tests.sh`

After a known-good setup, export distro snapshot:

```powershell
wsl --export smarthouse-dev C:\temp\smarthouse-dev-baseline.tar
```

Then teammates can import the same baseline as a fresh named distro:

```powershell
wsl --import smarthouse-dev C:\WSL\smarthouse-dev C:\temp\smarthouse-dev-baseline.tar --version 2
```

This produces a reproducible environment without changing their existing distros.

## 9. Troubleshooting

- Docker command missing in Windows terminal:
  - Use WSL terminal commands directly.
- Services fail at startup after full restart:
  - Re-run `docker compose up -d` and then verification.
- MQTT/auth issues:
  - Check `docs/MQTT_SECURITY_OPERATIONS_RUNBOOK.md`.
