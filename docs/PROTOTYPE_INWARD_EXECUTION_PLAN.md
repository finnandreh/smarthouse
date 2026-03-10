# Prototype Inward Execution Plan

## Goal

Build a usable prototype without overbuilding by:

1. Completing missing skeleton contracts first.
2. Validating one end-to-end loop.
3. Hardening inward only after each shell is stable.

This follows the master spec while keeping scope tight.

## Missing Skeleton Items To Add First

These are the highest-value gaps relative to `docs/PROJECT_MASTER_SPEC.md`.

1. Discovery contract parity
- Add `platform/discovery` publish/subscribe support in SDK + registry.
- Keep existing `device_announce` on `platform/{house}/{device}/event` for compatibility.
- Add tests that assert both paths work.

2. QoS policy skeleton
- Introduce centralized QoS policy by message kind (`event`, `telemetry`, `control`, `status`, `config`).
- Start with defaults from spec:
  - telemetry: QoS 0
  - control/config: QoS 1
  - critical event class: QoS 2
- Make policy configurable via env for prototype tuning.

3. Telemetry persistence abstraction
- Keep current API, add storage interface skeleton (`writer` contract) with in-memory and Postgres stub implementations.
- Add retention config keys and no-op pruning job scaffold.
- Do not add a full TSDB yet.

4. Observability plumbing skeleton
- Keep observability API baseline.
- Add generated scrape target config artifact contract (even if minimal).
- Add one minimal metrics endpoint contract in core services (`/metrics` placeholder).

5. Firmware reference template scaffold
- Add `firmware_reference/` structure and architecture notes (ESP32-first template layout).
- Include boot workflow, identity, MQTT client, OTA hook stubs as interfaces only.

## Prototype Scope Lock (Do This Before Any Expansion)

Definition of done for the first prototype:

1. Device (sim or SDK client) announces.
2. Registry records/updates device.
3. Device emits motion event.
4. Automation engine publishes control command.
5. Device handles control and publishes state/event ack.
6. Telemetry ingest endpoint accepts and acknowledges points.

If all six pass with scripts/tests, the prototype is valid.

## Inward Build Sequence

Phase A: Outer skeleton completion
- Implement the five missing skeleton items above.
- Add contract tests only.
- Avoid deep logic.

Phase A progress update (2026-03-10):
- Completed: discovery dual-path support.
- Completed: QoS policy skeleton wiring.
- Completed: telemetry writer + retention placeholders.
- Completed: core service `/metrics` placeholder endpoints.
- Completed: `firmware_reference/` ESP32 interface scaffold.

Phase B: Prototype loop stabilization
- Run and stabilize end-to-end loop tests.
- Fix reliability bugs (idempotency, reconnect, publish confirmation, payload consistency).

Phase B progress update (2026-03-10):
- Completed: house-designer JSON contract schema and mapping document.
- Completed: baseline parts/BOM generator from house-designer JSON.
- Policy: frontend remains prototype-first; frontend hardening deferred until prototype review sign-off.

Phase C: First inner hardening
- Add minimal persistence for telemetry.
- Add auth boundaries to phase 7-15 services where absent.
- Add observability signal quality checks.

Phase D: Controlled expansion
- Add more protocols, installer workflows, and cloud sync depth only after A-C are green.

## Guardrails (Prevent Building Too Big Too Early)

1. No feature merges without matching verification script/test.
2. Prefer interface and contract stubs over full subsystem implementation.
3. Ship one protocol path deeply before broad protocol expansion.
4. Keep local-first behavior as non-negotiable acceptance criteria.
5. Every new phase must preserve prototype loop reliability.

## Immediate Next 3 Tasks

Status snapshot (2026-03-10):

1. Completed: discovery dual-path skeleton (`platform/discovery` + existing announce flow).
2. Completed: shared QoS policy module and publisher wiring in SDK, registry, automation, and bridge base.
3. Completed: telemetry writer interface with in-memory + Postgres stub and retention placeholders.
