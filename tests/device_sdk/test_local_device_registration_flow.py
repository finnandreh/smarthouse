import unittest
from unittest.mock import patch

from device_sdk.core.auth import AuthTokenResponse
from device_sdk.core.registry import RegistryResponse
from device_sdk.examples import local_device


class _FakeMqttClient:
    def set_control_handler(self, handler):
        self._handler = handler

    def connect(self):
        return None

    def publish_event(self, payload):
        return None

    def publish_discovery(self, payload):
        return None

    def publish_status(self, payload):
        return None

    def publish_telemetry(self, payload):
        return None

    def disconnect(self):
        return None


class LocalDeviceRegistrationFlowTests(unittest.TestCase):
    def _args(self, **overrides):
        base = {
            "house": "home01",
            "device_id": "sdk-dev",
            "device_type": "relay_module",
            "protocol": "",
            "target": "esp32",
            "mqtt_host": "localhost",
            "mqtt_port": 8883,
            "ca_cert": "certs/ca.crt",
            "client_cert": "certs/esp32-simulator.crt",
            "client_key": "certs/esp32-simulator.key",
            "registry_url": "http://localhost:8081",
            "registry_token": "",
            "provisioning_key": "",
            "token_subject": "",
            "token_role": "provisioner",
            "token_scopes": "device:register",
            "token_expires_minutes": 30,
            "require_registry_registration": False,
            "interval_seconds": 0.0,
            "max_iterations": 0,
        }
        base.update(overrides)
        return type("Args", (), base)()

    @patch("device_sdk.examples.local_device.time.sleep", return_value=None)
    @patch("device_sdk.examples.local_device._create_mqtt_client", return_value=_FakeMqttClient())
    @patch("device_sdk.examples.local_device.signal.signal", return_value=None)
    @patch("device_sdk.examples.local_device.parse_args")
    def test_requires_registration_fails_without_token(self, mock_parse_args, *_):
        mock_parse_args.return_value = self._args(require_registry_registration=True)
        with self.assertRaises(RuntimeError):
            local_device.run()

    @patch("device_sdk.examples.local_device.time.sleep", return_value=None)
    @patch("device_sdk.examples.local_device._create_mqtt_client", return_value=_FakeMqttClient())
    @patch("device_sdk.examples.local_device.signal.signal", return_value=None)
    @patch("device_sdk.examples.local_device.DeviceRegistryClient")
    @patch("device_sdk.examples.local_device.ProvisioningAuthClient")
    @patch("device_sdk.examples.local_device.parse_args")
    def test_bootstrap_registration_success(self, mock_parse_args, mock_auth_client_cls, mock_registry_cls, *_):
        mock_parse_args.return_value = self._args(
            provisioning_key="changeme-provisioning-local-dev",
            require_registry_registration=True,
            max_iterations=1,
        )

        mock_auth_client = mock_auth_client_cls.return_value
        mock_auth_client.issue_token.return_value = AuthTokenResponse(
            status_code=200,
            body={"access_token": "token-abc"},
        )

        mock_registry = mock_registry_cls.return_value
        mock_registry.register_device.return_value = RegistryResponse(status_code=200, body={"registered": True})

        result = local_device.run()
        self.assertEqual(result, 0)
        mock_auth_client.issue_token.assert_called_once()
        mock_registry.register_device.assert_called_once()


if __name__ == "__main__":
    unittest.main()
