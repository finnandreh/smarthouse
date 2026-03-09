from typing import Dict, List

# Capability presets keyed by high-level device class.
CAPABILITY_CATALOG: Dict[str, List[str]] = {
    "relay_module": ["relay_output", "power_monitor"],
    "dimmer_module": ["dimmer_output", "power_monitor"],
    "thermostat": ["temperature_sensor", "hvac_mode", "setpoint_control"],
    "sensor_node": ["motion_sensor", "temperature_sensor", "battery_level"],
}


def capabilities_for_device_class(device_class: str) -> List[str]:
    key = device_class.strip().lower()
    if key not in CAPABILITY_CATALOG:
        raise ValueError(f"Unknown device class: {device_class}")
    return list(CAPABILITY_CATALOG[key])
