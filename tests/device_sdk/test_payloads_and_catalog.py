import unittest

from device_sdk.capabilities.catalog import capabilities_for_device_class
from device_sdk.capabilities.payloads import (
    build_announce_payload,
    build_control_ack_payload,
    build_event_payload,
)
from device_sdk.core.models import DeviceDescriptor


class PayloadAndCatalogTests(unittest.TestCase):
    def setUp(self):
        self.device = DeviceDescriptor(
            id="dev-1",
            house="home01",
            type="relay_module",
            protocol="wifi",
            capabilities=["relay_output"],
        )

    def test_announce_payload_shape(self):
        payload = build_announce_payload(self.device)
        self.assertEqual(payload["event"], "device_announce")
        self.assertEqual(payload["type"], "relay_module")
        self.assertIn("timestamp", payload)

    def test_event_payload_with_metadata(self):
        payload = build_event_payload("relay_state", "ON", metadata={"source": "test"})
        self.assertEqual(payload["event"], "relay_state")
        self.assertEqual(payload["value"], "ON")
        self.assertEqual(payload["metadata"]["source"], "test")

    def test_control_ack_payload_reason_optional(self):
        payload = build_control_ack_payload("set_relay", applied=False, reason="Unsupported")
        self.assertFalse(payload["applied"])
        self.assertEqual(payload["reason"], "Unsupported")

    def test_catalog_lookup(self):
        caps = capabilities_for_device_class("Thermostat")
        self.assertIn("temperature_sensor", caps)

    def test_catalog_unknown_class(self):
        with self.assertRaises(ValueError):
            capabilities_for_device_class("unknown")


if __name__ == "__main__":
    unittest.main()
