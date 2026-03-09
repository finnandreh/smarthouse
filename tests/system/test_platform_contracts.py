import json
import unittest
from urllib.request import urlopen


def get_json(url: str) -> dict:
    with urlopen(url, timeout=5) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


class PlatformContractsTests(unittest.TestCase):
    def test_project_engine_health(self) -> None:
        payload = get_json("http://localhost:8085/health")
        self.assertEqual(payload.get("status"), "ok")

    def test_system_generator_health(self) -> None:
        payload = get_json("http://localhost:8086/health")
        self.assertEqual(payload.get("status"), "ok")

    def test_cloud_services_health(self) -> None:
        payload = get_json("http://localhost:8087/health")
        self.assertEqual(payload.get("status"), "ok")

    def test_installer_platform_health(self) -> None:
        payload = get_json("http://localhost:8088/health")
        self.assertEqual(payload.get("status"), "ok")

    def test_telemetry_health(self) -> None:
        payload = get_json("http://localhost:8089/health")
        self.assertEqual(payload.get("status"), "ok")

    def test_ai_health(self) -> None:
        payload = get_json("http://localhost:8090/health")
        self.assertEqual(payload.get("status"), "ok")

    def test_observability_health(self) -> None:
        payload = get_json("http://localhost:8094/health")
        self.assertEqual(payload.get("status"), "ok")


if __name__ == "__main__":
    unittest.main()
