# Documentation Index

## Core

- Architecture spec: `docs/COPILOT_DEVELOPMENT_ORCHESTRATOR.md`
- Phase scaffold tracker: `docs/PHASE_SCAFFOLD_STATUS.md`
- User journey flow diagram (draw.io, 2 pages: system map + timeline): `docs/SYSTEM_USER_FLOW_OVERVIEW.drawio`
- Device SDK baseline docs: `device_sdk/README.md`
- MQTT topic model: `docs/TOPIC_CONVENTIONS.md`
- MQTT security + operations runbook: `docs/MQTT_SECURITY_OPERATIONS_RUNBOOK.md`
- Edge credential rotation runbook: `docs/EDGE_CREDENTIAL_ROTATION_RUNBOOK.md`
- Onboarding checklist: `docs/ONBOARDING_CHECKLIST.md`
- Project quickstart and command reference: `README.md`

## Workflows

- Stack verification CI: `.github/workflows/stack-verification.yml`
- Edge controller verification CI: `.github/workflows/edge-controller-verification.yml`
- Device SDK verification CI: `.github/workflows/device-sdk-verification.yml`
- Project engine verification CI: `.github/workflows/project-engine-verification.yml`
- System generator verification CI: `.github/workflows/system-generator-verification.yml`
- Cloud services verification CI: `.github/workflows/cloud-services-verification.yml`
- Installer platform verification CI: `.github/workflows/installer-platform-verification.yml`
- Telemetry verification CI: `.github/workflows/telemetry-verification.yml`
- AI service verification CI: `.github/workflows/ai-verification.yml`
- Observability verification CI: `.github/workflows/observability-verification.yml`
- System tests verification CI: `.github/workflows/system-tests-verification.yml`
- Monthly guarded cert rotation CI: `.github/workflows/cert-rotation-guarded.yml`
- Monthly JWT lifecycle security CI: `.github/workflows/jwt-security-lifecycle.yml`
- PR-scoped JWT lifecycle security CI: `.github/workflows/jwt-security-lifecycle-pr.yml`

## Script Categories

- Full verification: `scripts/run_full_verification.sh`
- Security verification: `scripts/verify_*.sh`
- Device SDK verification: `scripts/verify_device_sdk.sh`, `scripts/verify_device_sdk_unit.sh`, `scripts/verify_device_sdk_bootstrap.sh`, `scripts/verify_device_sdk_mqtt_integration.sh`
- Project engine verification: `scripts/verify_project_engine.sh`
- System generator verification: `scripts/verify_system_generator.sh`
- Cloud services verification: `scripts/verify_cloud_services.sh`
- Installer platform verification: `scripts/verify_installer_platform.sh`
- Telemetry verification: `scripts/verify_telemetry.sh`
- AI verification: `scripts/verify_ai_service.sh`
- Observability verification: `scripts/verify_observability.sh`
- System test verification: `scripts/verify_system_tests.sh`
- Phase scaffold integrity verification: `scripts/verify_phase_scaffold_integrity.sh`
- Edge credential rotation: `scripts/rotate_edge_api_keys.sh`
- Edge control verification: `scripts/verify_edge_controller.sh`, `scripts/verify_edge_maintenance_recovery.sh`
- Certificate lifecycle: `scripts/generate_mqtt_tls_certs.sh`, `scripts/issue_client_cert.sh`, `scripts/revoke_client_cert.sh`, `scripts/rotate_service_certs.sh`, `scripts/rotate_with_guardrails.sh`, `scripts/rotate_service_zero_downtime.sh`, `scripts/finalize_zero_downtime_rotation.sh`
- Monitoring and scheduling: `scripts/check_cert_expiry.sh`, `scripts/check_mqtt_security_events.sh`, `scripts/install_local_security_cron.sh`
