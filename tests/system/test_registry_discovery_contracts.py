import json
import subprocess
import time
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def _get_json(url: str) -> tuple[int, dict]:
    try:
        with urlopen(url, timeout=5) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body)
    except HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


class RegistryDiscoveryContractsTests(unittest.TestCase):
    mqtt_container = "smarthouse-mqtt"

    def _docker_exec(self, command: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["docker", "exec", self.mqtt_container, "sh", "-lc", command],
            check=False,
            capture_output=True,
            text=True,
        )

    def _publish(self, topic: str, payload: dict) -> None:
        message = json.dumps(payload).replace("'", "'\"'\"'")
        cmd = (
            "mosquitto_pub "
            "--cafile /mosquitto/config/certs/ca.crt "
            "--cert /mosquitto/config/certs/test-client.crt "
            "--key /mosquitto/config/certs/test-client.key "
            "-p 8883 -h localhost "
            f"-t {topic} -m '{message}'"
        )
        result = self._docker_exec(cmd)
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout or "publish failed")

    def _registry_ready_or_skip(self):
        try:
            status, payload = _get_json("http://localhost:8081/health")
        except (URLError, TimeoutError):
            self.skipTest("device-registry not reachable")
            return

        if status != 200 or payload.get("status") != "ok":
            self.skipTest("device-registry not healthy")

    def _docker_ready_or_skip(self):
        result = subprocess.run(["docker", "ps"], check=False, capture_output=True, text=True)
        if result.returncode != 0:
            self.skipTest("docker not available")

        check = self._docker_exec("echo ok")
        if check.returncode != 0:
            self.skipTest("mqtt container not available")

    def test_registry_accepts_discovery_and_announce_paths(self) -> None:
        self._registry_ready_or_skip()
        self._docker_ready_or_skip()

        stamp = str(int(time.time()))
        house = "home01"
        discovery_id = f"disc-{stamp}"
        announce_id = f"ann-{stamp}"

        self._publish(
            "platform/discovery",
            {
                "device_id": discovery_id,
                "house": house,
                "device_type": "relay_module",
                "protocol": "mqtt",
                "firmware_version": "0.1.0",
                "capabilities": ["relay_output", "power_monitor"],
            },
        )

        self._publish(
            f"platform/{house}/{announce_id}/event",
            {
                "event": "device_announce",
                "type": "relay_module",
                "protocol": "wifi",
                "capabilities": ["relay_output"],
            },
        )

        time.sleep(2)

        status_disc, body_disc = _get_json(f"http://localhost:8081/devices/{discovery_id}")
        status_ann, body_ann = _get_json(f"http://localhost:8081/devices/{announce_id}")

        self.assertEqual(status_disc, 200)
        self.assertEqual(status_ann, 200)
        self.assertEqual(body_disc.get("house"), house)
        self.assertEqual(body_ann.get("house"), house)


if __name__ == "__main__":
    unittest.main()
