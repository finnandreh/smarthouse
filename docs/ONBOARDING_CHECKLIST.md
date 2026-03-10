# Onboarding Checklist

Use this checklist for a new developer/operator onboarding this SmartHouse stack.

## 1. Environment

- [ ] Install Docker + Compose in WSL distro (`smarthouse-dev` recommended).
- [ ] Confirm Docker works: `docker --version` and `docker compose version`.
- [ ] Confirm WSL distro is running and has access to workspace path `/mnt/c/smarthouse`.

## 2. Read Core Docs

- [ ] Read architecture baseline: `docs/COPILOT_DEVELOPMENT_ORCHESTRATOR.md`.
- [ ] Read start-here design flow: `docs/START_HERE_DESIGN_FLOW.md`.
- [ ] Read reproducible WSL setup guide: `docs/WSL_REPRODUCIBLE_SETUP.md`.
- [ ] Read VS Code exact setup guide: `docs/VS_CODE_EXACT_SETUP.md`.
- [ ] Read internal setup and operations index: `docs/INTERNAL_SETUP_AND_OPERATIONS.md`.
- [ ] Read MQTT topic conventions: `docs/TOPIC_CONVENTIONS.md`.
- [ ] Read security runbook: `docs/MQTT_SECURITY_OPERATIONS_RUNBOOK.md`.
- [ ] Read house designer JSON contract: `docs/HOUSE_DESIGNER_JSON_CONTRACT.md`.

## 3. Generate Certificates

- [ ] Run cert generation:

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && chmod +x scripts/generate_mqtt_tls_certs.sh && scripts/generate_mqtt_tls_certs.sh"
```

- [ ] Verify CA private key is outside workspace (`/home/<user>/.smarthouse-secrets/ca/ca.key`).

## 4. Start Stack

- [ ] Build and start services:

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && docker compose up -d --build"
```

- [ ] Confirm containers up: `docker compose ps`.
- [ ] Confirm APIs healthy: `http://localhost:8081/health`, `http://localhost:8082/health`.

## 5. Run Full Verification

- [ ] Run full suite:

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && chmod +x scripts/run_full_verification.sh && scripts/run_full_verification.sh"
```

- [ ] Confirm output includes `FULL_VERIFICATION=passed`.

## 6. Install Local Security Checks

- [ ] Install cron checks:

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && chmod +x scripts/install_local_security_cron.sh && scripts/install_local_security_cron.sh"
```

- [ ] Verify cron entries:

```bash
wsl -d smarthouse-dev -- bash -lc "crontab -l | grep smarthouse-security-check"
```

## 7. Learn Operational Commands

- [ ] Issue cert: `scripts/issue_client_cert.sh <name>`.
- [ ] Revoke cert: `scripts/revoke_client_cert.sh <name>`.
- [ ] Guarded rotation: `scripts/rotate_with_guardrails.sh`.
- [ ] Zero-downtime rotate: `scripts/rotate_service_zero_downtime.sh <service>`.
- [ ] Finalize overlap: `scripts/finalize_zero_downtime_rotation.sh <service> <old-cert-path>`.

## 8. CI Awareness

- [ ] Review push/PR verification workflow: `.github/workflows/stack-verification.yml`.
- [ ] Review edge controller verification workflow: `.github/workflows/edge-controller-verification.yml`.
- [ ] Review device SDK verification workflow: `.github/workflows/device-sdk-verification.yml`.
- [ ] Review monthly guarded rotation workflow: `.github/workflows/cert-rotation-guarded.yml`.
- [ ] Review monthly JWT lifecycle security workflow: `.github/workflows/jwt-security-lifecycle.yml`.
- [ ] Review PR-scoped JWT lifecycle security workflow: `.github/workflows/jwt-security-lifecycle-pr.yml`.
- [ ] Review stack edge-controller verification step in `.github/workflows/stack-verification.yml`.

## 9. First-Day Validation (Recommended)

- [ ] Run `scripts/check_cert_expiry.sh` and `scripts/check_mqtt_security_events.sh`.
- [ ] Run one bridge event test (`/emit-test` endpoint on any bridge).
- [ ] Confirm DB persistence using `scripts/verify_persistence.sh`.

## 10. Escalation Path

If anything fails:

- [ ] Check MQTT logs: `docker compose logs mqtt --no-color --tail=200`.
- [ ] Re-run `scripts/run_full_verification.sh`.
- [ ] Follow incident/troubleshooting in `docs/MQTT_SECURITY_OPERATIONS_RUNBOOK.md`.

## 11. Design Entry (House Designer)

- [ ] Open `web/house_designer/index.html` and create a sample client/property/room hierarchy.
- [ ] Export JSON and validate shape against `examples/house_designer/client_demo.json`.
- [ ] Generate parts list with `scripts/generate_parts_list.py`.
