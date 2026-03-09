import argparse
import signal
import time
from typing import Dict

from device_sdk.capabilities.payloads import (
    build_announce_payload,
    build_control_ack_payload,
    build_event_payload,
    build_status_payload,
    build_telemetry_payload,
)
from device_sdk.capabilities.catalog import capabilities_for_device_class
from device_sdk.core.auth import AuthTokenRequest, ProvisioningAuthClient
from device_sdk.core.models import DeviceDescriptor
from device_sdk.core.registry import DeviceRegistryClient
from device_sdk.core.targets import get_target_profile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SmartHouse SDK sample local device")
    parser.add_argument("--house", default="home01")
    parser.add_argument("--device-id", default="sdk-device-01")
    parser.add_argument("--device-type", default="relay_module")
    parser.add_argument("--protocol", default="")
    parser.add_argument("--target", default="esp32", choices=["esp32", "stm32", "rp2040", "linux"])
    parser.add_argument("--mqtt-host", default="localhost")
    parser.add_argument("--mqtt-port", type=int, default=8883)
    parser.add_argument("--ca-cert", default="certs/ca.crt")
    parser.add_argument("--client-cert", default="certs/esp32-simulator.crt")
    parser.add_argument("--client-key", default="certs/esp32-simulator.key")
    parser.add_argument("--registry-url", default="http://localhost:8081")
    parser.add_argument("--registry-token", default="")
    parser.add_argument("--provisioning-key", default="")
    parser.add_argument("--token-subject", default="")
    parser.add_argument("--token-role", default="provisioner")
    parser.add_argument("--token-scopes", default="device:register")
    parser.add_argument("--token-expires-minutes", type=int, default=30)
    parser.add_argument("--require-registry-registration", action="store_true")
    parser.add_argument("--interval-seconds", type=float, default=5.0)
    parser.add_argument("--max-iterations", type=int, default=0)
    return parser.parse_args()


def _create_mqtt_client(args: argparse.Namespace, device: DeviceDescriptor):
    # Import transport lazily so argument parsing/tests work even without MQTT extras installed.
    from device_sdk.transports.mqtt.client import MqttDeviceClient, MqttTlsConfig

    return MqttDeviceClient(
        device=device,
        host=args.mqtt_host,
        port=args.mqtt_port,
        tls_config=MqttTlsConfig(
            ca_cert_path=args.ca_cert,
            client_cert_path=args.client_cert,
            client_key_path=args.client_key,
        ),
    )


def run() -> int:
    args = parse_args()
    running = True

    def stop_handler(*_):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    profile = get_target_profile(args.target)
    protocol = args.protocol or profile.protocol
    try:
        class_capabilities = capabilities_for_device_class(args.device_type)
    except ValueError:
        class_capabilities = []

    merged_capabilities = sorted(set(profile.capabilities + class_capabilities))

    device = DeviceDescriptor(
        id=args.device_id,
        house=args.house,
        type=args.device_type,
        protocol=protocol,
        capabilities=merged_capabilities,
    )

    registry_token = args.registry_token
    if not registry_token and args.provisioning_key:
        token_subject = args.token_subject or f"sdk-{args.device_id}"
        token_scopes = [scope.strip() for scope in args.token_scopes.split(",") if scope.strip()]
        auth_client = ProvisioningAuthClient(base_url=args.registry_url, provisioning_key=args.provisioning_key)
        token_response = auth_client.issue_token(
            AuthTokenRequest(
                subject=token_subject,
                role=args.token_role,
                house=device.house,
                scopes=token_scopes,
                expires_minutes=args.token_expires_minutes,
            )
        )
        if token_response.access_token:
            registry_token = token_response.access_token
            print("Issued registry token via provisioning key")
        else:
            print(f"Token issuance failed status={token_response.status_code} body={token_response.body}")
            if args.require_registry_registration:
                raise RuntimeError("Token issuance failed while --require-registry-registration is enabled")

    if registry_token:
        registry = DeviceRegistryClient(base_url=args.registry_url, bearer_token=registry_token)
        registry_response = registry.register_device(device)
        print(f"Registry status={registry_response.status_code} body={registry_response.body}")
        if args.require_registry_registration and registry_response.status_code != 200:
            raise RuntimeError(f"Registry registration failed with status {registry_response.status_code}")
    elif args.require_registry_registration:
        raise RuntimeError("No registry token available while --require-registry-registration is enabled")

    mqtt_client = _create_mqtt_client(args, device)

    relay_state: Dict[str, str] = {"value": "OFF"}

    def on_control(payload: dict) -> dict:
        action = str(payload.get("action", ""))
        if action == "set_relay":
            relay_state["value"] = str(payload.get("value", relay_state["value"]))
            return build_control_ack_payload(action=action, applied=True)
        return build_control_ack_payload(action=action or "unknown", applied=False, reason="Unsupported action")

    mqtt_client.set_control_handler(on_control)
    mqtt_client.connect()
    print("Device connected, publishing announce and periodic telemetry/event updates")

    mqtt_client.publish_event(build_announce_payload(device))
    mqtt_client.publish_status(build_status_payload(status="online"))

    watts = 120.0
    iterations = 0
    try:
        while running:
            watts += 0.7
            mqtt_client.publish_telemetry(build_telemetry_payload(metrics={"power_watts": round(watts, 2)}))
            mqtt_client.publish_event(
                build_event_payload(
                    event="relay_state",
                    value=relay_state["value"],
                )
            )
            iterations += 1
            if args.max_iterations > 0 and iterations >= args.max_iterations:
                break
            time.sleep(args.interval_seconds)
    finally:
        mqtt_client.publish_status(build_status_payload(status="offline"))
        mqtt_client.disconnect()
        print("Device disconnected")

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
