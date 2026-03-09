"""MQTT transport module."""

try:
	from .client import MqttDeviceClient, MqttTlsConfig
except ModuleNotFoundError:  # pragma: no cover - optional in minimal environments
	MqttDeviceClient = None
	MqttTlsConfig = None

__all__ = ["MqttDeviceClient", "MqttTlsConfig"]
