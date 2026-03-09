from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class TargetProfile:
    name: str
    protocol: str
    capabilities: List[str]


TARGET_PROFILES: Dict[str, TargetProfile] = {
    "esp32": TargetProfile(
        name="esp32",
        protocol="wifi",
        capabilities=["relay_output", "power_monitor", "ota_update"],
    ),
    "stm32": TargetProfile(
        name="stm32",
        protocol="ethernet",
        capabilities=["relay_output", "digital_input", "watchdog"],
    ),
    "rp2040": TargetProfile(
        name="rp2040",
        protocol="wifi",
        capabilities=["relay_output", "temperature_sensor", "heartbeat"],
    ),
    "linux": TargetProfile(
        name="linux",
        protocol="ethernet",
        capabilities=["relay_output", "power_monitor", "diagnostics"],
    ),
}


def get_target_profile(name: str) -> TargetProfile:
    key = name.strip().lower()
    if key not in TARGET_PROFILES:
        raise ValueError(f"Unknown target profile: {name}")
    return TARGET_PROFILES[key]
