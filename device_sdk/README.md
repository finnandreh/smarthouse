# SmartHouse Device SDK

Phase 6 baseline Python SDK for local SmartHouse devices.

## Included modules

- `device_sdk/core/models.py`: device descriptor model shared by transport and registry helpers.
- `device_sdk/core/topics.py`: canonical SmartHouse topic builder/parser.
- `device_sdk/core/targets.py`: target profiles for ESP32/STM32/RP2040/Linux defaults.
- `device_sdk/core/registry.py`: registry registration helper (`/devices/register`).
- `device_sdk/transports/mqtt/client.py`: secure MQTT client with mTLS and control subscription handling.
- `device_sdk/capabilities/catalog.py`: capability catalog by device class.
- `device_sdk/capabilities/payloads.py`: common JSON payload builders for announce, telemetry, status, and control acknowledgements.
- `device_sdk/examples/local_device.py`: runnable sample device loop.

## Quick run

From repository root:

```bash
python -m pip install -r device_sdk/requirements.txt
```

Then run:

```bash
python -m device_sdk.examples.local_device \
  --target esp32 \
  --house home01 \
  --device-id sdk-device-01 \
  --mqtt-host localhost \
  --mqtt-port 8883 \
  --ca-cert certs/ca.crt \
  --client-cert certs/esp32-simulator.crt \
  --client-key certs/esp32-simulator.key
```

Notes:

- `--target` selects protocol/capability defaults (`esp32`, `stm32`, `rp2040`, `linux`).
- `--device-type` contributes additional capabilities from the catalog when known.
- `--protocol` overrides the target default protocol when provided.
- `DeviceRegistryClient` includes configurable retries for transient network errors.
- MQTT transport requires `paho-mqtt`; top-level SDK imports still work in minimal environments without it.

Optional registry registration (requires Bearer token with `device:register` scope):

```bash
python -m device_sdk.examples.local_device \
  --registry-url http://localhost:8081 \
  --registry-token "${TOKEN}"
```

Provisioning-key bootstrap mode (SDK requests token then registers):

```bash
python -m device_sdk.examples.local_device \
  --registry-url http://localhost:8081 \
  --provisioning-key changeme-provisioning-local-dev \
  --token-role provisioner \
  --token-scopes device:register
```

Add `--require-registry-registration` to fail fast when token issuance or device registration does not succeed.

Legacy-compatible simulator entrypoint (now SDK-backed):

```bash
python examples/devices/esp32_simulator.py
```

Installer bootstrap utility (token + registration without MQTT runtime):

```bash
python -m device_sdk.examples.bootstrap_register \
  --registry-url http://localhost:8081 \
  --provisioning-key changeme-provisioning-local-dev \
  --subject installer-bootstrap-001 \
  --house home01 \
  --device-id sdk-bootstrap-001 \
  --require-lookup
```

Unit verification includes wrapper behavior coverage in `tests/device_sdk/test_esp32_simulator_wrapper.py`.
Registration bootstrap behavior is covered in `tests/device_sdk/test_local_device_registration_flow.py`.
