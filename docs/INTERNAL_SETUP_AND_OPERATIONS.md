# Internal Setup and Operations

This document holds installation and operational entry points for team/internal use.

Use this instead of the public-facing `README.md` for environment replication and day-1 operations.

## Purpose

1. Keep GitHub-facing project description concise and architecture-focused.
2. Keep detailed setup, tooling, and operations references in internal docs.

## Setup Entry Points

- Reproducible WSL workflow: `docs/WSL_REPRODUCIBLE_SETUP.md`
- Exact VS Code + `.venv` replication: `docs/VS_CODE_EXACT_SETUP.md`
- New team-member checklist: `docs/ONBOARDING_CHECKLIST.md`

## Runtime and Verification Entry Points

- Main docs index: `docs/DOCUMENTATION_INDEX.md`
- Full verification: `scripts/run_full_verification.sh`
- System-level verification: `scripts/verify_system_tests.sh`
- Discovery dual-path verification: `scripts/verify_registry_discovery_dual_path.sh`

## Security and Lifecycle Operations

- MQTT security runbook: `docs/MQTT_SECURITY_OPERATIONS_RUNBOOK.md`
- Edge credential rotation: `docs/EDGE_CREDENTIAL_ROTATION_RUNBOOK.md`
- Certificate lifecycle scripts:
  - `scripts/generate_mqtt_tls_certs.sh`
  - `scripts/issue_client_cert.sh`
  - `scripts/revoke_client_cert.sh`
  - `scripts/rotate_with_guardrails.sh`
  - `scripts/rotate_service_zero_downtime.sh`
  - `scripts/finalize_zero_downtime_rotation.sh`

## Notes for Future Changes

If setup procedures change:

1. Update this file first.
2. Update `docs/WSL_REPRODUCIBLE_SETUP.md` and/or `docs/VS_CODE_EXACT_SETUP.md`.
3. Keep top-level `README.md` focused on product description, architecture, and navigation.
