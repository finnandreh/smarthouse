import io
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from device_sdk.core.models import DeviceDescriptor
from device_sdk.core.registry import DeviceRegistryClient


class _FakeResponse:
    def __init__(self, status, body):
        self.status = status
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class RegistryClientTests(unittest.TestCase):
    def setUp(self):
        self.device = DeviceDescriptor(
            id="dev-1",
            house="home01",
            type="relay_module",
            protocol="wifi",
            capabilities=["relay_output"],
        )

    def test_register_success(self):
        client = DeviceRegistryClient("http://localhost:8081", "token")
        response = _FakeResponse(200, b'{"registered": true}')
        with patch("device_sdk.core.registry.request.urlopen", return_value=response):
            result = client.register_device(self.device)
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.body["registered"])

    def test_register_http_error_json(self):
        client = DeviceRegistryClient("http://localhost:8081", "token")
        error = HTTPError(
            url="http://localhost:8081/devices/register",
            code=403,
            msg="Forbidden",
            hdrs=None,
            fp=io.BytesIO(b'{"detail":"forbidden"}'),
        )
        with patch("device_sdk.core.registry.request.urlopen", side_effect=error):
            result = client.register_device(self.device)
        self.assertEqual(result.status_code, 403)
        self.assertEqual(result.body["detail"], "forbidden")

    def test_register_network_error_retries_then_returns_unreachable(self):
        client = DeviceRegistryClient(
            "http://localhost:8081",
            "token",
            max_retries=2,
            retry_backoff_seconds=0,
        )
        with patch("device_sdk.core.registry.request.urlopen", side_effect=URLError("down")) as mocked_urlopen:
            with patch("device_sdk.core.registry.time.sleep"):
                result = client.register_device(self.device)
        self.assertEqual(mocked_urlopen.call_count, 3)
        self.assertEqual(result.status_code, 0)
        self.assertIn("Registry unreachable", result.body["detail"])


if __name__ == "__main__":
    unittest.main()
