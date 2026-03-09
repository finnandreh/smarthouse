import unittest

import device_sdk


class PackageImportTests(unittest.TestCase):
    def test_top_level_exports(self):
        self.assertIsNotNone(device_sdk.DeviceDescriptor)
        self.assertIsNotNone(device_sdk.AuthTokenRequest)
        self.assertIsNotNone(device_sdk.DeviceRegistryClient)
        self.assertIsNotNone(device_sdk.ProvisioningAuthClient)
        self.assertIsNotNone(device_sdk.get_target_profile)


if __name__ == "__main__":
    unittest.main()
