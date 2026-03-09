import unittest
from unittest.mock import patch

from device_sdk.core.auth import AuthTokenResponse
from device_sdk.core.registry import RegistryResponse
from device_sdk.examples import bootstrap_register


class BootstrapRegisterExampleTests(unittest.TestCase):
    def _args(self, **overrides):
        base = {
            "registry_url": "http://localhost:8081",
            "provisioning_key": "changeme-provisioning-local-dev",
            "subject": "installer-test",
            "house": "home01",
            "device_id": "sdk-bootstrap-001",
            "device_type": "relay_module",
            "protocol": "wifi",
            "capabilities": "relay_output,power_monitor",
            "token_role": "provisioner",
            "token_scopes": "device:register",
            "token_expires_minutes": 15,
            "require_lookup": False,
        }
        base.update(overrides)
        return type("Args", (), base)()

    @patch("device_sdk.examples.bootstrap_register.parse_args")
    @patch("device_sdk.examples.bootstrap_register.DeviceRegistryClient")
    @patch("device_sdk.examples.bootstrap_register.ProvisioningAuthClient")
    def test_run_success(self, mock_auth_cls, mock_registry_cls, mock_parse_args):
        mock_parse_args.return_value = self._args()
        mock_auth = mock_auth_cls.return_value
        mock_auth.issue_token.return_value = AuthTokenResponse(status_code=200, body={"access_token": "abc"})
        mock_registry = mock_registry_cls.return_value
        mock_registry.register_device.return_value = RegistryResponse(status_code=200, body={"registered": True})

        result = bootstrap_register.run()
        self.assertEqual(result, 0)
        mock_auth.issue_token.assert_called_once()
        mock_registry.register_device.assert_called_once()

    @patch("device_sdk.examples.bootstrap_register.parse_args")
    @patch("device_sdk.examples.bootstrap_register.ProvisioningAuthClient")
    def test_run_fails_when_token_issue_fails(self, mock_auth_cls, mock_parse_args):
        mock_parse_args.return_value = self._args()
        mock_auth = mock_auth_cls.return_value
        mock_auth.issue_token.return_value = AuthTokenResponse(status_code=401, body={"detail": "Unauthorized"})

        with self.assertRaises(RuntimeError):
            bootstrap_register.run()


if __name__ == "__main__":
    unittest.main()
