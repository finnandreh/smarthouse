# Start Here: Design Flow

Use this path when handing the project to someone new and asking them to start system design.

## 1. Run the Platform

From Windows:

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && docker compose up -d --build"
```

Optional confidence check:

```bash
wsl -d smarthouse-dev -- bash -lc "cd /mnt/c/smarthouse && scripts/verify_system_tests.sh"
```

## 2. Build Client Design in House Designer

Open:

- `web/house_designer/index.html`

Create the hierarchy:

- client
- properties/addresses
- subjects (house/garage/gate/etc)
- floors
- rooms
- units

Download the JSON from the UI.

## 3. Validate the JSON Contract

Contract reference:

- `docs/HOUSE_DESIGNER_JSON_CONTRACT.md`
- `schemas/house_designer_config.schema.json`

Use the demo as a shape reference:

- `examples/house_designer/client_demo.json`

## 4. Generate First Artifact (Parts/BOM)

```bash
C:/smarthouse/.venv/Scripts/python.exe scripts/generate_parts_list.py --input examples/house_designer/client_demo.json --output C:/smarthouse/logs/parts_demo.json
```

Output example:

- `logs/parts_demo.json`

## 5. What Comes Next

The same JSON is intended to drive:

- device topology generation
- provisioning plans
- project/system generation contracts
- installer outputs

Keep this rule:

- House Designer JSON is the source-of-truth input for generation steps.
