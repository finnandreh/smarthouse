import json
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import paho.mqtt.client as mqtt

from device_sdk.core.models import DeviceDescriptor
from device_sdk.core.topics import build_topic, parse_topic

ControlHandler = Callable[[dict], Optional[dict]]


@dataclass(frozen=True)
class MqttTlsConfig:
    ca_cert_path: str
    client_cert_path: str
    client_key_path: str


class MqttDeviceClient:
    """Secure MQTT client wrapper following SmartHouse topic conventions."""

    def __init__(
        self,
        device: DeviceDescriptor,
        host: str,
        port: int,
        tls_config: MqttTlsConfig,
        client_id: Optional[str] = None,
        publish_retries: int = 2,
        publish_retry_backoff_seconds: float = 0.2,
        publish_wait_timeout_seconds: float = 5.0,
        require_publish_confirmation: bool = False,
    ):
        self.device = device
        self.host = host
        self.port = port
        self.tls_config = tls_config
        self._connected = threading.Event()
        self._control_handler: Optional[ControlHandler] = None
        self._publish_retries = max(0, publish_retries)
        self._publish_retry_backoff_seconds = max(0.0, publish_retry_backoff_seconds)
        self._publish_wait_timeout_seconds = max(0.1, publish_wait_timeout_seconds)
        self._require_publish_confirmation = require_publish_confirmation
        self._in_message_handler = False
        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id or f"device-sdk-{device.id}",
        )
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.tls_set(
            ca_certs=self.tls_config.ca_cert_path,
            certfile=self.tls_config.client_cert_path,
            keyfile=self.tls_config.client_key_path,
        )

    def connect(self, keepalive: int = 60, timeout_seconds: float = 10.0):
        self._client.connect(self.host, self.port, keepalive=keepalive)
        self._client.loop_start()
        if not self._connected.wait(timeout=timeout_seconds):
            raise TimeoutError("Timed out waiting for MQTT connection")

    def disconnect(self):
        self._client.loop_stop()
        self._client.disconnect()
        self._connected.clear()

    def set_control_handler(self, handler: ControlHandler):
        self._control_handler = handler

    def publish_event(self, payload: dict, qos: int = 1):
        self._publish_json("event", payload, qos=qos)

    def publish_telemetry(self, payload: dict, qos: int = 1):
        self._publish_json("telemetry", payload, qos=qos)

    def publish_status(self, payload: dict, qos: int = 1):
        self._publish_json("status", payload, qos=qos)

    def publish_config(self, payload: dict, qos: int = 1):
        self._publish_json("config", payload, qos=qos)

    def _publish_json(self, kind: str, payload: dict, qos: int = 1):
        topic = build_topic(self.device.house, self.device.id, kind)
        msg = json.dumps(payload)

        last_error = "unknown"
        for attempt in range(self._publish_retries + 1):
            result = self._client.publish(topic, msg, qos=qos)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                if qos > 0 and self._require_publish_confirmation and not self._in_message_handler:
                    result.wait_for_publish(timeout=self._publish_wait_timeout_seconds)
                    if not result.is_published():
                        last_error = "publish_timeout"
                    else:
                        return
                else:
                    return
            else:
                last_error = f"rc={result.rc}"

            if attempt < self._publish_retries:
                time.sleep(self._publish_retry_backoff_seconds)

        raise RuntimeError(f"Failed to publish MQTT message to {topic}: {last_error}")

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code != 0:
            return
        control_topic = build_topic(self.device.house, self.device.id, "control")
        client.subscribe(control_topic)
        self._connected.set()

    def _on_message(self, client, userdata, message):
        try:
            _, _, kind = parse_topic(message.topic)
            if kind != "control":
                return
            payload = json.loads(message.payload.decode("utf-8"))
        except (ValueError, json.JSONDecodeError):
            return

        if self._control_handler:
            self._in_message_handler = True
            try:
                response_payload = self._control_handler(payload)
                if response_payload is not None:
                    self.publish_event(response_payload)
            finally:
                self._in_message_handler = False
