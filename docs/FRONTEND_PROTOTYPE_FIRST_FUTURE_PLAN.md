# Frontend Prototype-First Future Plan

This file is the working plan for frontend evolution and Copilot next tasks.

Status decision (2026-03-10):

- Backend is considered hardened enough for current prototype milestones.
- Frontend must stay prototype-first.
- Do not start frontend hardening until prototype review sign-off is complete.

## 1. Frontend Policy (Important)

1. Build and review prototypes first.
2. Confirm UX and model fit with stakeholders before hardening.
3. Harden only after explicit "prototype accepted" decision.
4. Keep JSON contract compatibility during all prototype iterations.

## 2. Frontend Scope Right Now

Primary artifact:

- `web/house_designer/index.html`

Source-of-truth contract:

- `schemas/house_designer_config.schema.json`
- `docs/HOUSE_DESIGNER_JSON_CONTRACT.md`

## 3. Frontend To-Do List (Prototype Phase)

P0 - Must Do Before Hardening:

1. Prototype review checklist with users/installers:
- hierarchy fit (`client -> property -> subject -> floor -> room -> unit`)
- naming clarity and field labels
- editing flow speed and confusion points
- mobile usability baseline

2. Improve editing ergonomics in prototype:
- add duplicate/copy actions for floors, rooms, and unit groups
- add reorder controls (up/down) for properties/subjects/floors/rooms/units
- add inline validation hints for required fields

3. Improve JSON lifecycle:
- add import button UX for local JSON files
- show schema validation errors in readable format
- preserve stable ordering in exported JSON

4. Add prototype test coverage:
- contract tests for invalid/missing hierarchy nodes
- parts-generation parity tests for edited prototype outputs

P1 - Should Do During Prototype Cycle:

1. Introduce view modes:
- structure view (current)
- parts summary preview

2. Improve accessibility baseline:
- keyboard navigation for add/remove flows
- focus management after add/remove operations

3. Prototype data safeguards:
- unsaved-changes warning before reset/import
- restore last autosave snapshot

4. Add a reusable sample gallery:
- small home
- villa with garage
- multi-property client

P2 - Later (Still Pre-Hardening):

1. Split UI into maintainable modules (if still single-file HTML).
2. Evaluate migration path to component framework only after UX sign-off.
3. Add lightweight design tokens and shared UI primitives.

## 4. Frontend Hardening Entry Criteria

Frontend hardening starts only when all are true:

1. Prototype review signed off.
2. P0 tasks complete.
3. JSON contract version strategy agreed.
4. Generator consumers confirm output sufficiency.

## 5. Frontend Hardening Backlog (After Sign-Off)

1. Security:
- strict input sanitization and escaping audits
- CSP and content loading rules
- dependency policy if framework/tooling is introduced

2. Reliability:
- end-to-end UI flows for import/edit/export
- deterministic export snapshots
- recovery from malformed JSON and partial edits

3. Performance:
- large model behavior (many properties/rooms/units)
- render/update latency budgets

4. Maintainability:
- typed model interfaces
- module boundaries
- CI checks for frontend lint/test/build path

## 6. Copilot Next Tasks (Clear Sequence)

Immediate next tasks for Copilot:

1. Add prototype review checklist doc and feedback template.
2. Implement P0 UX actions: duplicate, reorder, inline required-field hints.
3. Add JSON file import workflow and readable validation errors in UI.
4. Add/extend tests for contract violations and generation parity.
5. Run local verification and record results in docs.

After prototype sign-off:

1. Create frontend hardening execution plan (security/reliability/performance).
2. Implement hardening in small PR-sized increments.
3. Keep JSON contract backward compatible or versioned with migration notes.

## 7. Framework Evolution Rule

This framework is intended to evolve.

When modified later:

1. Keep this file updated as the canonical frontend plan.
2. Update `docs/DOCUMENTATION_INDEX.md` links if file names change.
3. Record decisions (what changed and why) in short dated entries.
