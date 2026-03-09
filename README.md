# SmartHouse Platform Scaffold

This repository is scaffolded as a local-first smart-home platform baseline.

## For Colleagues

Current delivery state:

- Phases 1-15 are scaffolded and have runnable baselines where applicable.
- Automated hardening checks are integrated into local scripts and CI workflows.
- Full verification target currently passes end-to-end.

If you are downloading this project for the first time:

1. Install Docker Desktop and WSL2 (distribution: `smarthouse-dev`).
2. Clone the repository and open it at `C:\smarthouse`.
3. Run the full verification command from this README before making changes.
4. Use phase-specific verification workflows/scripts when modifying scoped areas.

Documentation:

- Index: `docs/DOCUMENTATION_INDEX.md`
- MQTT security runbook: `docs/MQTT_SECURITY_OPERATIONS_RUNBOOK.md`
- Onboarding checklist: `docs/ONBOARDING_CHECKLIST.md`

## Included in this scaffold

- MQTT broker (`Eclipse Mosquitto`)
- `device-registry` service for device announce/register
- `automation-engine` service for event-driven rules
- Shared topic conventions and capability schema
- Device SDK baseline (`device_sdk`) for local secure clients
- Example device simulator publisher

## Quick start

### 1) Start the stack

Generate local TLS certificates first:

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && chmod +x scripts/generate_mqtt_tls_certs.sh && scripts/generate_mqtt_tls_certs.sh"
```

By default, the CA private key is stored outside the workspace at:

- `/home/<user>/.smarthouse-secrets/ca/ca.key`

```bash
docker compose up --build
```

Services:

- MQTT TLS: `localhost:8883`
- PostgreSQL: `localhost:5432`
- Device Registry API: `http://localhost:8081`
- Automation Engine API: `http://localhost:8082`
- Modbus Bridge API: `http://localhost:8091`
- KNX Bridge API: `http://localhost:8092`
- BACnet Bridge API: `http://localhost:8093`
- Edge Controller API: `http://localhost:8084`
- Project Engine API: `http://localhost:8085`
- System Generator API: `http://localhost:8086`
- Cloud Services API: `http://localhost:8087`
- Installer Platform API: `http://localhost:8088`
- Telemetry API: `http://localhost:8089`
- AI Service API: `http://localhost:8090`
- Observability API: `http://localhost:8094`

Default local credentials:

- MQTT identity auth: per-service client certificates (CN-based)
- MQTT CA cert: `certs/ca.crt`
- Example client cert: `certs/test-client.crt`
- Example client key: `certs/test-client.key`
- Provisioning bootstrap header for token issuance: `x-provisioning-key: changeme-provisioning-local-dev`

Protected HTTP APIs use Bearer JWTs with `role`, `house`, and `scopes` claims.

Default RBAC policy:

- `operator`: `device:register`
- `provisioner`: `device:register`
- `automation-admin`: `rules:reload`
- `admin`: all current scopes

Auth endpoints are rate limited (`AUTH_RATE_LIMIT_WINDOW_SECONDS` / `AUTH_RATE_LIMIT_MAX_REQUESTS`) and write allow/deny audit events to `auth_security_events`.
JWT signing supports key rotation using `kid` (`JWT_ACTIVE_KID`) and optional fallback verification key (`JWT_PREVIOUS_KID` + `JWT_PREVIOUS_SECRET`).

Issue a scoped token:

```bash
curl -X POST http://localhost:8081/auth/token \
  -H "Content-Type: application/json" \
  -H "x-provisioning-key: changeme-provisioning-local-dev" \
  -d '{
    "subject": "local-operator",
    "role": "operator",
    "house": "home01",
    "scopes": ["device:register"],
    "expires_minutes": 30
  }'
```

Example token helper:

```bash
TOKEN=$(scripts/auth_token.sh local-operator operator home01 device:register 30)
```

Revoke a token (admin or equivalent scope):

```bash
ADMIN_TOKEN=$(scripts/auth_token.sh local-admin admin home01 rules:reload 30)

curl -X POST http://localhost:8081/auth/revoke \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d "{\"token\":\"${TOKEN}\"}"
```

### 2) Register a sample device

```bash
curl -X POST http://localhost:8081/devices/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{
    "id": "device123",
    "house": "home01",
    "type": "relay_module",
    "protocol": "wifi",
    "capabilities": ["relay_output", "power_monitor"]
  }'
```

### 3) Publish an event (motion)

Use any MQTT client to publish:

- topic: `platform/home01/device123/event`
- TLS CA cert: `certs/ca.crt`
- mTLS client cert/key: `certs/test-client.crt` + `certs/test-client.key`
- payload:

```json
{"event":"motion_detected","value":true}
```

If `after_sunset` condition is true in the rule, automation engine publishes:

- topic: `platform/home01/device123/control`
- payload:

```json
{"action":"set_relay","value":"ON"}
```

### 4) Reload rules without restart

```bash
TOKEN=$(scripts/auth_token.sh local-admin admin home01 rules:reload 30)

curl -X POST http://localhost:8082/rules/reload
  -H "Authorization: Bearer ${TOKEN}"
```

### 5) Emit normalized bridge test events

```bash
curl -X POST http://localhost:8091/emit-test -H "Content-Type: application/json" -d '{"event":"register_read","value":230.1}'
curl -X POST http://localhost:8092/emit-test -H "Content-Type: application/json" -d '{"event":"group_write","value":1}'
curl -X POST http://localhost:8093/emit-test -H "Content-Type: application/json" -d '{"event":"analog_input","value":22.8}'
```

Manual MQTT publish example:

```bash
mosquitto_pub --cafile certs/ca.crt --cert certs/test-client.crt --key certs/test-client.key -p 8883 -h localhost -t platform/home01/device123/event -m '{"event":"motion_detected","value":true}'
```

Each bridge converts protocol-native payloads to the internal MQTT event model and publishes to:

- `platform/{house}/{device}/event`

### 6) Edge controller operations

Aggregated dependency health:

```bash
curl -X GET http://localhost:8084/health/dependencies
```

Provision device through edge controller:

```bash
curl -X POST http://localhost:8084/provision/device \
  -H "Content-Type: application/json" \
  -H "x-edge-api-key: changeme-edge-local-dev" \
  -d '{
    "id": "edge-device-1",
    "house": "home01",
    "type": "relay_module",
    "protocol": "wifi",
    "capabilities": ["relay_output"]
  }'
```

## Project layout

```text
config/
  automation/rules.yaml
docs/
cloud_services/
examples/
  devices/esp32_simulator.py  # SDK-backed compatibility entrypoint
installer_platform/
monitoring/
mosquitto/
  mosquitto.conf
schemas/
  device_capability.schema.json
services/
  automation_engine/
  bridge_bacnet/
  bridge_common/
  bridge_knx/
  bridge_modbus/
  device_registry/
  edge_controller/
  project_engine/
  system_generator/
  telemetry/
  ai/
tests/
  system/
device_sdk/
  core/
  transports/mqtt/
  capabilities/
  examples/
docker-compose.yml
```

## Next milestones

1. Add MQTT auth/TLS certificates and secure provisioning flow
2. Build local dashboard and installer workflows
3. Add protocol-specific drivers in each bridge service
4. Add CI/CD and integration tests for all protocols

## Verification

Run full local verification suite (WSL):

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && chmod +x scripts/run_full_verification.sh && scripts/run_full_verification.sh"
```

Run scaffold and project-engine-only checks:

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && chmod +x scripts/verify_phase_scaffold_integrity.sh scripts/verify_project_engine.sh && scripts/verify_phase_scaffold_integrity.sh && scripts/verify_project_engine.sh"
```

Run only Device SDK verification (including MQTT integration):

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && chmod +x scripts/verify_device_sdk.sh scripts/verify_device_sdk_unit.sh scripts/verify_device_sdk_bootstrap.sh scripts/verify_device_sdk_mqtt_integration.sh && scripts/verify_device_sdk.sh && scripts/verify_device_sdk_unit.sh && scripts/verify_device_sdk_bootstrap.sh && scripts/verify_device_sdk_mqtt_integration.sh"
```

CI verification runs automatically on every push and pull request via:

- `.github/workflows/stack-verification.yml`
- `.github/workflows/edge-controller-verification.yml`
- `.github/workflows/device-sdk-verification.yml`
- `.github/workflows/project-engine-verification.yml`
- `.github/workflows/system-generator-verification.yml`
- `.github/workflows/cloud-services-verification.yml`
- `.github/workflows/installer-platform-verification.yml`
- `.github/workflows/telemetry-verification.yml`
- `.github/workflows/ai-verification.yml`
- `.github/workflows/observability-verification.yml`
- `.github/workflows/system-tests-verification.yml`

Monthly JWT security lifecycle checks run via:

- `.github/workflows/jwt-security-lifecycle.yml`

PR-scoped JWT lifecycle checks (path-filtered auth/security changes) run via:

- `.github/workflows/jwt-security-lifecycle-pr.yml`

## Certificate Lifecycle

Issue an extra client certificate:

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && chmod +x scripts/issue_client_cert.sh && scripts/issue_client_cert.sh my-client"
```

Revoke a client certificate and regenerate CRL:

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && chmod +x scripts/revoke_client_cert.sh && scripts/revoke_client_cert.sh my-client"
```

Rotate service certificates and restart dependent services:

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && chmod +x scripts/rotate_service_certs.sh && scripts/rotate_service_certs.sh"
```

Guarded rotation with automatic rollback on failed checks:

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && chmod +x scripts/rotate_with_guardrails.sh && scripts/rotate_with_guardrails.sh"
```

Set backup retention count (default: `14`):

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && BACKUP_RETENTION=7 scripts/rotate_with_guardrails.sh"
```

Set max total backup size in MB (default: `0`, disabled):

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && BACKUP_MAX_MB=50 scripts/rotate_with_guardrails.sh"
```

Validate revocation enforcement:

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && chmod +x scripts/verify_revocation.sh && scripts/verify_revocation.sh"
```

Run local certificate expiry and MQTT security event checks:

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && chmod +x scripts/check_cert_expiry.sh scripts/check_mqtt_security_events.sh && scripts/check_cert_expiry.sh && scripts/check_mqtt_security_events.sh"
```

Run JWT security lifecycle checks (revocation, key-id rotation compatibility, revoked-token pruning):

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && chmod +x scripts/verify_auth_security_controls.sh scripts/verify_jwt_kid_rotation.sh scripts/verify_revoked_token_prune.sh && scripts/verify_auth_security_controls.sh && scripts/verify_jwt_kid_rotation.sh && scripts/verify_revoked_token_prune.sh"
```

Install daily local cron security checks:

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && chmod +x scripts/install_local_security_cron.sh && scripts/install_local_security_cron.sh"
```

The cron installer now includes revoked-token prune maintenance via `scripts/prune_revoked_tokens.sh`.

Zero-downtime dual-cert overlap rotation for one service:

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && chmod +x scripts/rotate_service_zero_downtime.sh && scripts/rotate_service_zero_downtime.sh device-registry"
```

Finalize overlap window and revoke old cert:

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && chmod +x scripts/finalize_zero_downtime_rotation.sh && scripts/finalize_zero_downtime_rotation.sh device-registry /mnt/c/smarthouse/certs/overlap/device-registry/<stamp>.prev.crt"
```

Scheduled guarded rotation runs monthly via:

- `.github/workflows/cert-rotation-guarded.yml`
