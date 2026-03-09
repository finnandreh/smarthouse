import json
import os
from typing import Any, Dict

import paho.mqtt.client as mqtt


class BridgeAdapterBase:
    def __init__(self, bridge_name: str):
        self.bridge_name = bridge_name
        self.mqtt_host = os.getenv("MQTT_HOST", "localhost")
        self.mqtt_port = int(os.getenv("MQTT_PORT", "8883"))
        self.mqtt_username = os.getenv("MQTT_USERNAME", "")
        self.mqtt_password = os.getenv("MQTT_PASSWORD", "")
        self.mqtt_tls_enabled = os.getenv("MQTT_TLS_ENABLED", "false").lower() == "true"
        self.mqtt_tls_ca_cert = os.getenv("MQTT_TLS_CA_CERT", "")
        self.mqtt_tls_client_cert = os.getenv("MQTT_TLS_CLIENT_CERT", "")
        self.mqtt_tls_client_key = os.getenv("MQTT_TLS_CLIENT_KEY", "")
        self.house_id = os.getenv("HOUSE_ID", "home01")
        self.device_id = os.getenv("DEVICE_ID", f"{bridge_name}-01")
        self.protocol = os.getenv("BRIDGE_PROTOCOL", bridge_name)
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"bridge-{bridge_name}")
        self._tls_configured = False

    def connect(self) -> None:
        if self.mqtt_username:
            self.client.username_pw_set(self.mqtt_username, self.mqtt_password)
        if self.mqtt_tls_enabled and not self._tls_configured:
            self.client.tls_set(
                ca_certs=self.mqtt_tls_ca_cert,
                certfile=self.mqtt_tls_client_cert,
                keyfile=self.mqtt_tls_client_key,
            )
            self._tls_configured = True
        self.client.connect(self.mqtt_host, self.mqtt_port, keepalive=60)
        self.client.loop_start()

    def close(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()

    def normalize_event(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "event": str(raw_payload.get("event", "bridge_event")),
            "source_protocol": self.protocol,
            "data": raw_payload,
        }

    def publish_event(self, raw_payload: Dict[str, Any]) -> None:
        topic = f"platform/{self.house_id}/{self.device_id}/event"
        payload = self.normalize_event(raw_payload)
        self.client.publish(topic, json.dumps(payload), qos=1)
