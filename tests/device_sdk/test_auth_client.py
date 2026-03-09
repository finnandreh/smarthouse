import io
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from device_sdk.core.auth import AuthTokenRequest, ProvisioningAuthClient


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


class AuthClientTests(unittest.TestCase):
    def setUp(self):
        self.request = AuthTokenRequest(
            subject="sdk-test",
            role="provisioner",
            house="home01",
            scopes=["device:register"],
            expires_minutes=15,
        )

    def test_issue_token_success(self):
        client = ProvisioningAuthClient("http://localhost:8081", "master-key")
        response = _FakeResponse(200, b'{"access_token":"abc","token_type":"bearer"}')
        with patch("device_sdk.core.auth.request.urlopen", return_value=response):
            result = client.issue_token(self.request)

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.access_token, "abc")

    def test_issue_token_http_error(self):
        client = ProvisioningAuthClient("http://localhost:8081", "master-key")
        error = HTTPError(
            url="http://localhost:8081/auth/token",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=io.BytesIO(b'{"detail":"Unauthorized"}'),
        )
        with patch("device_sdk.core.auth.request.urlopen", side_effect=error):
            result = client.issue_token(self.request)

        self.assertEqual(result.status_code, 401)
        self.assertEqual(result.body.get("detail"), "Unauthorized")

    def test_issue_token_network_error_retries(self):
        client = ProvisioningAuthClient(
            "http://localhost:8081",
            "master-key",
            max_retries=2,
            retry_backoff_seconds=0,
        )
        with patch("device_sdk.core.auth.request.urlopen", side_effect=URLError("down")) as mocked_urlopen:
            with patch("device_sdk.core.auth.time.sleep"):
                result = client.issue_token(self.request)

        self.assertEqual(mocked_urlopen.call_count, 3)
        self.assertEqual(result.status_code, 0)
        self.assertIn("Auth endpoint unreachable", str(result.body.get("detail", "")))


if __name__ == "__main__":
    unittest.main()
