# ESP32 Template Skeleton

This folder defines an interface-level template for an ESP32 device runtime.

Current status:
- Architecture and module boundaries only.
- No production firmware logic yet.

Expected module mapping:
- interfaces/device_identity.h
- interfaces/mqtt_client.h
- interfaces/ota_updater.h
- interfaces/capability_handler.h

Acceptance criteria for first implementation pass:
- Publish discovery and status.
- Handle control commands.
- Publish telemetry and event payloads compatible with SmartHouse topic conventions.
- Keep local-safe fallback behavior when connectivity is unavailable.
