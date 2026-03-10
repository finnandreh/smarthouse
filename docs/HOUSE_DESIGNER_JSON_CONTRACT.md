# House Designer JSON Contract

This document defines how `web/house_designer/index.html` JSON is used as the canonical input for Copilot-driven system generation.

## Canonical Input

- Source UI: `web/house_designer/index.html`
- Contract schema: `schemas/house_designer_config.schema.json`
- Demo input: `examples/house_designer/client_demo.json`

## Hierarchy

1. `client`
2. `properties[]` (address/location)
3. `subjects[]` (house/garage/gate/etc)
4. `floors[]`
5. `rooms[]`
6. `units[]`

## Artifact Mapping

- Device topology:
  - derived from all `units[]` with location path
  - output target: project and system generation contracts

- Parts / BOM:
  - aggregate `units[].type` by `units[].quantity`
  - generator: `scripts/generate_parts_list.py`

- Provisioning plan:
  - location path and unit identities become install/provision records
  - output target: installer and edge provisioning workflows

## First Automation Commands

Generate parts list JSON:

```bash
C:/smarthouse/.venv/Scripts/python.exe scripts/generate_parts_list.py --input examples/house_designer/client_demo.json --output /tmp/parts.json
```

## Rules

1. Treat the house designer JSON as source-of-truth.
2. Version the contract; do not break existing versions silently.
3. Add validation before generation.
4. Add tests whenever mapping logic changes.
