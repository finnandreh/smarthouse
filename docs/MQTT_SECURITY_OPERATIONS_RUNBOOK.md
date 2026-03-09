# MQTT Security Operations Runbook

## Purpose

This runbook is the authoritative operations guide for the SmartHouse MQTT security model.
It covers setup, lifecycle management, verification, monitoring, and incident handling.

## Security Model (Current State)

- MQTT transport is TLS-only on port `8883`.
- Broker requires mutual TLS (`require_certificate true`).
- Broker identity is derived from certificate CN (`use_identity_as_username true`).
- Authorization is enforced by ACL rules (`mosquitto/aclfile`).
- Certificate revocation is enforced via CRL (`crlfile /mosquitto/config/certs/ca.crl`).
- Protected API endpoints use Bearer JWTs (issuer `device-registry`) with scoped claims.
- Protected API endpoints enforce per-IP rate limits via `AUTH_RATE_LIMIT_WINDOW_SECONDS` and `AUTH_RATE_LIMIT_MAX_REQUESTS`.
- Auth decisions (allow/deny) are persisted to `auth_security_events` for audit review.

## Key Files

- Broker config: `mosquitto/mosquitto.conf`
- Broker ACLs: `mosquitto/aclfile`
- Compose stack: `docker-compose.yml`
- TLS/PKI artifacts (public + service certs): `certs/`
- CA private material and CA DB (local secure path): `/home/<user>/.smarthouse-secrets/ca/`

## Service Identities (Certificate CN)

- `device-registry`
- `automation-engine`
- `bridge-modbus`
- `bridge-knx`
- `bridge-bacnet`
- `test-client` (verification utility identity)
- `esp32-simulator` (example/dev identity)

## First-Time Setup

1. Generate TLS and identity certs.

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && chmod +x scripts/generate_mqtt_tls_certs.sh && scripts/generate_mqtt_tls_certs.sh"
```

2. Start stack.

```bash
docker compose up -d --build
```

3. Run full verification suite.

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && chmod +x scripts/run_full_verification.sh && scripts/run_full_verification.sh"
```

## Verification Matrix

- `scripts/verify_mqtt_auth.sh`: mTLS required, authenticated publish works.
- `scripts/verify_revocation.sh`: revoked cert is blocked by CRL.
- `scripts/verify_acl_enforcement.sh`: identity ACL boundaries hold.
- `scripts/verify_plaintext_disabled.sh`: non-TLS/invalid transport path fails.
- `scripts/smoke_test_e2e.sh`: end-to-end event -> automation -> control flow.
- `scripts/verify_persistence.sh`: DB persistence path remains operational.
- `scripts/verify_auth_and_bridges.sh`: JWT protection and bridge endpoints still valid.
- `scripts/verify_auth_security_controls.sh`: token revocation denylist and auth control behavior.
- `scripts/verify_jwt_kid_rotation.sh`: active/previous `kid` verification and unknown `kid` rejection.
- `scripts/verify_revoked_token_prune.sh`: expired revoked-token cleanup validation.
- `scripts/verify_bridge_mqtt_flow.sh`: bridge event normalization and publish path.

## Certificate Lifecycle Operations

### Issue a New Client Certificate

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && scripts/issue_client_cert.sh my-client"
```

Advanced form (explicit CN/output prefix):

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && scripts/issue_client_cert.sh my-client --cn my-client --out-prefix my-client-v2"
```

### Revoke a Certificate

By client name:

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && scripts/revoke_client_cert.sh my-client"
```

By cert path:

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && scripts/revoke_client_cert.sh --cert /mnt/c/smarthouse/certs/overlap/device-registry/<stamp>.prev.crt"
```

### Rotate Service Certificates (Bulk)

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && scripts/rotate_service_certs.sh"
```

### Guarded Rotation (Backup + Checks + Rollback)

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && scripts/rotate_with_guardrails.sh"
```

Optional retention controls:

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && BACKUP_RETENTION=7 BACKUP_MAX_MB=50 scripts/rotate_with_guardrails.sh"
```

### Zero-Downtime Overlap Rotation (Single Service)

1. Rotate one service while preserving CN identity and overlap evidence.

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && scripts/rotate_service_zero_downtime.sh device-registry"
```

2. Finalize by revoking previous cert.

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && scripts/finalize_zero_downtime_rotation.sh device-registry /mnt/c/smarthouse/certs/overlap/device-registry/<stamp>.prev.crt"
```

## Monitoring and Local Scheduling

### Manual checks

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && scripts/check_cert_expiry.sh && scripts/check_mqtt_security_events.sh"
```

JWT revoke/prune maintenance:

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && scripts/prune_revoked_tokens.sh"
```

### Install local cron checks

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && scripts/install_local_security_cron.sh"
```

Writes to:

- `logs/security-checks.log`

## CI/CD Workflows

- Stack verification on push/PR:
  - `.github/workflows/stack-verification.yml`
- Edge controller verification on push/PR paths:
  - `.github/workflows/edge-controller-verification.yml`
- Monthly guarded certificate rotation:
  - `.github/workflows/cert-rotation-guarded.yml`
- Monthly JWT lifecycle security checks:
  - `.github/workflows/jwt-security-lifecycle.yml`
- PR-scoped JWT lifecycle checks (path-filtered):
  - `.github/workflows/jwt-security-lifecycle-pr.yml`

## Incident Response Quick Actions

### Suspected certificate compromise

1. Revoke compromised cert immediately.
2. Restart MQTT service.
3. Re-issue replacement cert.
4. Restart affected service.
5. Run verification suite.

Example:

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && scripts/revoke_client_cert.sh bridge-knx && docker compose restart mqtt && scripts/issue_client_cert.sh bridge-knx && docker compose restart bridge-knx && scripts/run_full_verification.sh"
```

### Unexpected auth or ACL denials

1. Check MQTT logs and security counters.
2. Validate cert CN and ACL user block alignment.
3. Verify cert validity and CRL state.

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && scripts/check_mqtt_security_events.sh && docker compose logs mqtt --no-color --tail=200"
```

## Troubleshooting

### Error: `peer did not return a certificate`

Cause: client did not provide mTLS cert.
Fix: provide `--cert` and `--key` and trusted `--cafile`.

### Error: `unknown ca`

Cause: client cert not signed by current trusted CA, or stale certs after CA regen.
Fix: regenerate certs and recreate stack:

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && scripts/run_full_verification.sh"
```

### Error: revoked cert still accepted

Cause: CRL not regenerated or broker not reloaded/restarted.
Fix: run revoke script and restart MQTT service.

### Build/cache snapshot errors

Cause: local Docker cache corruption.
Fix:

```bash
wsl -d smarthouse-dev -- bash -lc "docker builder prune -af && docker system prune -af"
```

## Change Control

When modifying MQTT security:

1. Update `mosquitto/mosquitto.conf` and/or `mosquitto/aclfile`.
2. Update relevant scripts.
3. Update this runbook and `README.md`.
4. Run `scripts/run_full_verification.sh`.
5. Confirm CI workflow still passes.
