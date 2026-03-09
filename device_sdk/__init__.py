"""SmartHouse device SDK baseline package."""

from .core.models import DeviceDescriptor
from .core.auth import AuthTokenRequest, ProvisioningAuthClient
from .core.registry import DeviceRegistryClient
from .core.targets import TargetProfile, get_target_profile

try:
    from .transports.mqtt.client import MqttDeviceClient, MqttTlsConfig
except ModuleNotFoundError:  # pragma: no cover - optional in minimal environments
    MqttDeviceClient = None
    MqttTlsConfig = None

__all__ = [
    "DeviceDescriptor",
    "AuthTokenRequest",
    "DeviceRegistryClient",
    "ProvisioningAuthClient",
    "TargetProfile",
    "get_target_profile",
    "MqttDeviceClient",
    "MqttTlsConfig",
]
