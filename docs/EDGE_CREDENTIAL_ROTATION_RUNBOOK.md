# Edge Credential Rotation Runbook

## Purpose
Rotate edge controller API credentials (`EDGE_API_KEY_ADMIN`, `EDGE_API_KEY_OPERATOR`) safely and consistently.

## Prerequisites
- Local admin access to the SmartHouse workspace.
- Docker Compose stack available.
- Current `.env` file in repository root (or use a custom file path).

## Rotation Script
- Script: `scripts/rotate_edge_api_keys.sh`
- Behavior:
  - Creates a timestamped backup of the target env file.
  - Generates new admin/operator tokens.
  - Updates `EDGE_API_KEY`, `EDGE_API_KEY_ADMIN`, and `EDGE_API_KEY_OPERATOR`.

## Procedure
1. Rotate keys.
```bash
scripts/rotate_edge_api_keys.sh
```

2. Restart edge controller to load new environment values.
```bash
docker compose up -d --force-recreate edge-controller
```

3. Verify admin key works.
```bash
curl -fsS http://localhost:8084/config -H "x-edge-api-key: <new-admin-key>"
```

4. Verify operator permissions are scoped.
```bash
curl -s -o /tmp/edge_reload_check.json -w "%{http_code}" -X POST http://localhost:8084/lifecycle/reload-automation -H "x-edge-api-key: <new-operator-key>"
```
Expected result: `403`.

## Rollback
1. Restore previous env file from backup path emitted by the rotation script.
2. Restart edge controller.
```bash
docker compose up -d --force-recreate edge-controller
```

## Notes
- Rotate keys during a maintenance window when possible.
- Keep backups in a secure location and remove old backups after verification.
- This runbook rotates edge API keys only; JWT secrets and MQTT certificates are handled by separate workflows.
