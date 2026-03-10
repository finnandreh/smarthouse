# System Test Framework (Phase 14 Runnable Baseline)

Purpose:
- Expand integration/system/protocol coverage for the SmartHouse platform.

Implemented baseline:
- Cross-service contract tests in `tests/system/test_platform_contracts.py`.
- Registry discovery dual-path contract test in `tests/system/test_registry_discovery_contracts.py`.
- Unified runner script: `scripts/verify_system_tests.sh`.
- Health contract coverage for phases 7, 8, 9, 10, 11, 12, and 15 services.

Next hardening pass:
- Add scenario-driven provisioning and lifecycle tests.
- Add protocol fixture matrix and synthetic device orchestration.
