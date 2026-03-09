#!/usr/bin/env bash
set -euo pipefail

cd /mnt/c/smarthouse

PYTHON_BIN="python3"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "python3 not found"
  exit 1
fi

"${PYTHON_BIN}" -m compileall device_sdk >/dev/null

"${PYTHON_BIN}" - <<'PY'
import device_sdk

from device_sdk.capabilities.catalog import capabilities_for_device_class
from device_sdk.capabilities.payloads import build_announce_payload
from device_sdk.core.models import DeviceDescriptor
from device_sdk.core.targets import get_target_profile
from device_sdk.core.topics import build_topic, parse_topic

profile = get_target_profile("esp32")
device = DeviceDescriptor(
    id="sdk-smoke-device",
    house="home01",
    type="relay_module",
    protocol=profile.protocol,
    capabilities=sorted(set(profile.capabilities + capabilities_for_device_class("relay_module"))),
)
topic = build_topic(device.house, device.id, "event")
parsed_house, parsed_device, parsed_kind = parse_topic(topic)
assert parsed_house == device.house
assert parsed_device == device.id
assert parsed_kind == "event"
announce = build_announce_payload(device)
assert announce["event"] == "device_announce"
assert announce["type"] == device.type
assert device_sdk.DeviceDescriptor is not None
print("DEVICE_SDK_SMOKE=passed")
PY

echo "VERIFY_DEVICE_SDK=passed"
