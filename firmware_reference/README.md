# Firmware Reference Scaffold

Purpose:
- Provide a reference architecture skeleton for real embedded firmware targets.
- Keep this as interface-first until prototype loop hardening is complete.

Targets in scope for scaffold:
- ESP32 (first template)
- STM32 (planned)
- RP2040 (planned)
- Linux device agent (planned)

Core runtime modules (reference model):
- bootloader
- security_layer
- network_manager
- mqtt_client
- device_identity
- capability_handler
- io_manager
- sensor_manager
- automation_client
- ota_updater
- diagnostics
- local_config_storage

Boot workflow:
1. initialize hardware
2. load local configuration
3. connect network
4. publish discovery
5. register with platform
6. receive configuration
7. start runtime tasks

This directory intentionally contains stubs and interfaces only.
Implementation details are deferred until prototype loop and contract tests remain stable.
