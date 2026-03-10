import unittest

from device_sdk.core.targets import get_target_profile
from device_sdk.core.topics import build_topic, discovery_topic, parse_topic


class TopicsAndTargetsTests(unittest.TestCase):
    def test_build_and_parse_topic_roundtrip(self):
        topic = build_topic("home01", "dev-1", "event")
        self.assertEqual(topic, "platform/home01/dev-1/event")
        self.assertEqual(parse_topic(topic), ("home01", "dev-1", "event"))

    def test_build_topic_rejects_unknown_kind(self):
        with self.assertRaises(ValueError):
            build_topic("home01", "dev-1", "unknown")

    def test_parse_topic_rejects_invalid_prefix(self):
        with self.assertRaises(ValueError):
            parse_topic("wrong/home01/dev-1/event")

    def test_discovery_topic(self):
        self.assertEqual(discovery_topic(), "platform/discovery")

    def test_get_target_profile(self):
        profile = get_target_profile("ESP32")
        self.assertEqual(profile.protocol, "wifi")
        self.assertIn("relay_output", profile.capabilities)

    def test_get_target_profile_unknown(self):
        with self.assertRaises(ValueError):
            get_target_profile("bad-target")


if __name__ == "__main__":
    unittest.main()
