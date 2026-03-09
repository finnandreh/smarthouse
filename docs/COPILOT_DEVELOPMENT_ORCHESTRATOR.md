# Copilot Development Orchestrator

## Purpose
This document guides GitHub Copilot development for the SmartHouse platform.
It defines current delivery status, the next major implementation step, and an optional backlog.

## Architecture Rules
- Local-first operation must work without cloud connectivity.
- MQTT is the canonical event bus for device and service communication.
- Device behavior must be capability-driven (no hardcoded device types).
- Services must stay modular and independently deployable.
- Protocol bridges must translate protocol-native traffic to internal MQTT events.

## Current Delivery Status
Completed or mostly completed in this repository:
- Phase 1: Core MQTT messaging foundation.
- Phase 2: Device registry service with persistence and registration APIs.
- Phase 3: Automation engine with event -> condition -> action flow.
- Phase 5: Protocol bridge scaffolds (Modbus, KNX, BACnet) and normalization.
- Phase 13: Device simulation baseline.
- Phase 4: Edge controller baseline (service scaffold, dependency health, provisioning proxy, lifecycle actions).
- Phase 6: Device SDK foundation baseline (`device_sdk` core/topic model, secure MQTT transport, registry helper, and local example runtime).
- Phase 7: House Designer backend scaffold (`services/project_engine`) with runnable API baseline and generation-contract handoff endpoint.
- Phase 8: System generator scaffold (`services/system_generator`) with runnable baseline API (`/health`, `/validate`, `/generate`).
- Phase 9: Installer platform scaffold (`installer_platform`) with runnable baseline API (`/health`, `/install/validate`, `/install/plan`).
- Phase 10: Cloud services scaffold (`cloud_services`) with runnable baseline API (`/health`, `/sync/preview`).
- Phase 11: Telemetry pipeline scaffold (`services/telemetry`) with runnable baseline API (`/health`, `/ingest/validate`, `/ingest/batch`).
- Phase 12: AI services scaffold (`services/ai`) with runnable baseline API (`/health`, `/optimize/validate`, `/optimize/plan`).
- Phase 14: Expanded system test framework scaffold (`tests/system`) with runnable contract test baseline.
- Phase 15: Observability stack scaffold (`monitoring`) with runnable baseline API (`/health`, `/targets/validate`, `/dashboards/preview`).
- Security hardening track:
  - MQTT TLS + mTLS + ACL + CRL.
  - JWT auth with RBAC, rate limits, audit events.
  - JWT revoke flow, kid key-rotation compatibility, lifecycle checks.

## Next Big Step
Phase 7-15 Hardening Pass (completed)

Goal:
- Harden all Phase 7-15 runnable baselines with stricter contract validation, persistence boundaries, auth/authorization constraints, and failure-mode integration tests.

Required components:
- Completed: cross-phase negative-path tests for project, generator, cloud, installer, telemetry, AI, and observability services.
- Completed: runnable system contract suite (`tests/system`) with unified verifier integration.
- Completed: phase-specific CI workflows for telemetry, AI, observability, and system-test verification.
- Completed: full-stack verification wiring for all phases 1-15 runnable baselines.

Minimum acceptance criteria:
- Completed: all phase verifiers enforce positive/negative path behavior with stable status-code contracts.
- Completed: full verification remains green with hardening checks and no optional skips.
- Completed: local-first operation preserved while cloud/AI/observability remain optional services.
- Completed: CI path-filtered workflows cover each phase-specific surface area.

## Next Big Step
Production Readiness Hardening (optional follow-up)

Goal:
- Add stricter authn/authz and audit persistence to phase 7-15 services, plus chaos/fault-injection testing.

Phase 4 completion evidence (done):
1. Completed: edge command endpoint for safe bridge lifecycle operations (reload/restart by bridge).
2. Completed: replay-safe provisioning idempotency key handling.
3. Completed: signed edge admin/operator credential rotation runbook + script.
4. Completed: edge reconciliation SLO metrics and alert-ready counters.
5. Completed: integration tests for maintenance lock semantics and recovery flows.

Phase 6 baseline evidence (done):
1. Completed: `device_sdk/core` device descriptor and topic utilities.
2. Completed: `device_sdk/transports/mqtt` secure mTLS client with control-topic handling.
3. Completed: `device_sdk/core/registry.py` registration helper aligned to `/devices/register`.
4. Completed: `device_sdk/capabilities/payloads.py` announce/status/telemetry/event/control-ack builders.
5. Completed: `device_sdk/examples/local_device.py` runnable local example loop.

Phase 6 hardening evidence (done):
1. Completed: SDK unit test suite expanded (`tests/device_sdk`) with auth/bootstrap, wrapper, and registration flow coverage.
2. Completed: SDK bootstrap registration utility (`device_sdk.examples.bootstrap_register`) and end-to-end verifier.
3. Completed: MQTT integration verifier hardened to be non-skippable via container fallback runtime when local extras are unavailable.
4. Completed: MQTT publish retry/backoff logic added in SDK transport client with callback-safe confirmation handling.

## Optional TODO Backlog
Everything below is optional and can be implemented after the Phase 4 completion gate.

- Edge controller future enhancements (optional):
- Add per-device maintenance lock (not only global lock).
- Add staged provisioning policy engine (house/site quotas, protocol policies).
- Add reconciliation remediation actions (not just drift detection).
- Add edge event stream endpoint for installer UI consumption.
- Add encrypted local secret storage abstraction for edge credentials.

- Phase 6: Device SDK (`device_sdk`) for ESP32/STM32/RP2040/Linux.
- Phase 7: House Designer backend (`services/project_engine`).
- Phase 8: System generator (`services/system_generator`).
- Phase 9: Installer platform (`installer_platform`).
- Phase 10: Cloud services (`cloud_services`) for remote and analytics.
- Phase 11: Telemetry pipeline (`services/telemetry`) to TSDB/stream processing.
- Phase 12: AI services (`services/ai`) for optimization and prediction.
- Phase 14: Expanded testing framework (`tests`) with protocol/system coverage.
- Phase 15: Observability stack (`monitoring`) with metrics/tracing dashboards.

## Copilot Prompt Starters
- Expand `device_sdk` capability catalog for relay, dimmer, thermostat, and sensor classes.
- Add a simulated command-processing loop with retries and QoS-aware MQTT publishes.
- Add SDK-side registration bootstrap helper for installer flows.
- Create SDK integration tests against local MQTT + registry stack.
