import json
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def request_json(method: str, url: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=data, method=method, headers=headers)
    try:
        with urlopen(request, timeout=5) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body)
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        return exc.code, json.loads(body)


class PhaseHardeningContractsTests(unittest.TestCase):
    def test_project_validate_rejects_unsupported_capability(self) -> None:
        payload = {
            "house_id": "home01",
            "project_name": "hardening-project-validate",
            "zones": [
                {
                    "zone_id": "garage",
                    "name": "Garage",
                    "devices": [
                        {
                            "device_id": "g-thermo-1",
                            "device_type": "thermostat",
                            "protocol": "wifi",
                            "capabilities": ["relay_output"],
                        }
                    ],
                }
            ],
        }
        status, body = request_json("POST", "http://localhost:8085/projects/validate", payload)
        self.assertEqual(status, 200)
        self.assertFalse(body.get("valid"))
        self.assertTrue(any("unsupported_capabilities" in err for err in body.get("errors", [])))

    def test_project_create_rejects_unknown_device_type(self) -> None:
        payload = {
            "house_id": "home01",
            "project_name": "hardening-project-create",
            "zones": [
                {
                    "zone_id": "lab",
                    "name": "Lab",
                    "devices": [
                        {
                            "device_id": "lab-x-1",
                            "device_type": "unknown_type",
                            "protocol": "wifi",
                            "capabilities": ["relay_output"],
                        }
                    ],
                }
            ],
        }
        status, body = request_json("POST", "http://localhost:8085/projects", payload)
        self.assertEqual(status, 422)
        self.assertEqual(body.get("detail", {}).get("code"), "PROJECT_VALIDATION_FAILED")

    def test_project_generation_contract_missing_project_is_404(self) -> None:
        status, body = request_json("GET", "http://localhost:8085/projects/missing-hardening/generation-contract")
        self.assertEqual(status, 404)
        self.assertIn("detail", body)

    def test_generator_validate_rejects_contract_version(self) -> None:
        payload = {
            "project_id": "project-hardening-1",
            "contract_version": "phase7-v0",
            "generated_at": "2026-03-09T00:00:00Z",
            "devices_by_protocol": {"wifi": []},
            "zone_count": 0,
        }
        status, body = request_json("POST", "http://localhost:8086/validate", payload)
        self.assertEqual(status, 200)
        self.assertFalse(body.get("valid"))
        self.assertIn("unsupported_contract_version", body.get("errors", []))

    def test_generator_generate_rejects_unsupported_mode(self) -> None:
        payload = {
            "contract": {
                "project_id": "project-hardening-2",
                "contract_version": "phase7-v1",
                "generated_at": "2026-03-09T00:00:00Z",
                "devices_by_protocol": {"wifi": []},
                "zone_count": 0,
            },
            "mode": "apply-now",
        }
        status, body = request_json("POST", "http://localhost:8086/generate", payload)
        self.assertEqual(status, 400)
        self.assertEqual(body.get("detail"), "Unsupported mode")

    def test_generator_generate_rejects_unsupported_protocol(self) -> None:
        payload = {
            "contract": {
                "project_id": "project-hardening-3",
                "contract_version": "phase7-v1",
                "generated_at": "2026-03-09T00:00:00Z",
                "devices_by_protocol": {
                    "zigbee": [
                        {
                            "device_id": "z-1",
                            "device_type": "sensor_node",
                            "protocol": "zigbee",
                            "capabilities": ["motion_sensor"],
                        }
                    ]
                },
                "zone_count": 1,
            },
            "mode": "dry-run",
        }
        status, body = request_json("POST", "http://localhost:8086/generate", payload)
        self.assertEqual(status, 422)
        self.assertEqual(body.get("detail", {}).get("code"), "CONTRACT_VALIDATION_FAILED")

    def test_cloud_preview_defaults_sections(self) -> None:
        payload = {
            "site_id": "site-hardening",
            "tenant_id": "tenant-hardening",
            "mode": "metadata-only",
            "include_sections": [],
        }
        status, body = request_json("POST", "http://localhost:8087/sync/preview", payload)
        self.assertEqual(status, 200)
        self.assertEqual(len(body.get("sections", [])), 3)
        self.assertEqual(body.get("estimated_records"), 75)

    def test_cloud_preview_rejects_missing_telemetry_section(self) -> None:
        payload = {
            "site_id": "site-hardening",
            "tenant_id": "tenant-hardening",
            "mode": "telemetry-summary",
            "include_sections": ["devices"],
        }
        status, body = request_json("POST", "http://localhost:8087/sync/preview", payload)
        self.assertEqual(status, 422)
        self.assertEqual(body.get("detail", {}).get("code"), "INVALID_SYNC_REQUEST")

    def test_installer_validate_requires_ha_precheck(self) -> None:
        payload = {
            "site_id": "site-hardening",
            "installer_id": "installer-hardening",
            "target": "edge-controller-ha",
            "package_version": "1.2.3",
            "channel": "stable",
            "include_steps": ["install"],
        }
        status, body = request_json("POST", "http://localhost:8088/install/validate", payload)
        self.assertEqual(status, 200)
        self.assertFalse(body.get("valid"))
        self.assertIn("ha_target_requires_step:ha-precheck", body.get("errors", []))

    def test_installer_plan_rejects_invalid_ha_steps(self) -> None:
        payload = {
            "site_id": "site-hardening",
            "installer_id": "installer-hardening",
            "target": "edge-controller-ha",
            "package_version": "1.2.3",
            "channel": "stable",
            "include_steps": ["install"],
        }
        status, body = request_json("POST", "http://localhost:8088/install/plan", payload)
        self.assertEqual(status, 422)
        self.assertEqual(body.get("detail", {}).get("code"), "INVALID_INSTALL_PLAN")

    def test_telemetry_validate_rejects_debug_metric_name(self) -> None:
        payload = {
            "house_id": "home01",
            "source_protocol": "mqtt",
            "points": [{"name": "debug_temp", "value": 20.1, "unit": "C"}],
        }
        status, body = request_json("POST", "http://localhost:8089/ingest/validate", payload)
        self.assertEqual(status, 200)
        self.assertFalse(body.get("valid"))
        self.assertTrue(any("disallowed_metric_name" in err for err in body.get("errors", [])))

    def test_telemetry_batch_rejects_debug_metric_name(self) -> None:
        payload = {
            "house_id": "home01",
            "source_protocol": "mqtt",
            "points": [{"name": "debug_temp", "value": 20.1, "unit": "C"}],
        }
        status, body = request_json("POST", "http://localhost:8089/ingest/batch", payload)
        self.assertEqual(status, 422)
        self.assertEqual(body.get("detail", {}).get("code"), "INVALID_TELEMETRY_BATCH")

    def test_ai_validate_requires_occupancy_for_comfort(self) -> None:
        payload = {
            "project_id": "project-hardening-ai-1",
            "objective": "comfort",
            "horizon_hours": 12,
            "signals": ["weather"],
        }
        status, body = request_json("POST", "http://localhost:8090/optimize/validate", payload)
        self.assertEqual(status, 200)
        self.assertFalse(body.get("valid"))
        self.assertIn("objective_comfort_requires_signal:occupancy", body.get("errors", []))

    def test_ai_plan_rejects_missing_required_signal(self) -> None:
        payload = {
            "project_id": "project-hardening-ai-2",
            "objective": "comfort",
            "horizon_hours": 12,
            "signals": ["weather"],
        }
        status, body = request_json("POST", "http://localhost:8090/optimize/plan", payload)
        self.assertEqual(status, 422)
        self.assertEqual(body.get("detail", {}).get("code"), "INVALID_OPTIMIZATION_REQUEST")

    def test_observability_validate_requires_device_registry_target(self) -> None:
        payload = {
            "environment": "local-dev",
            "scrape_targets": ["edge-controller"],
        }
        status, body = request_json("POST", "http://localhost:8094/targets/validate", payload)
        self.assertEqual(status, 200)
        self.assertFalse(body.get("valid"))
        self.assertIn("missing_required_target:device-registry", body.get("errors", []))


if __name__ == "__main__":
    unittest.main()
