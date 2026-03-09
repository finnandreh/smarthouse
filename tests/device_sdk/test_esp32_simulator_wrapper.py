import unittest
from unittest.mock import patch

from examples.devices import esp32_simulator


class Esp32SimulatorWrapperTests(unittest.TestCase):
    def test_main_invokes_sdk_runtime(self):
        with patch("examples.devices.esp32_simulator._run_sdk_local_device", return_value=0) as mocked_run:
            with patch(
                "examples.devices.esp32_simulator.parse_args",
                return_value=type(
                    "Args",
                    (),
                    {
                        "house": "home01",
                        "device_id": "device123",
                        "mqtt_host": "localhost",
                        "mqtt_port": 8883,
                        "ca_cert": "certs/ca.crt",
                        "client_cert": "certs/esp32-simulator.crt",
                        "client_key": "certs/esp32-simulator.key",
                        "interval_seconds": 1.0,
                        "max_iterations": 1,
                        "registry_url": "http://localhost:8081",
                        "registry_token": "",
                    },
                )(),
            ):
                result = esp32_simulator.main()

        self.assertEqual(result, 0)
        mocked_run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
