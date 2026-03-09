"""Backward-compatible ESP32 simulator entrypoint using the Device SDK."""

import argparse
import sys


def _run_sdk_local_device() -> int:
    from device_sdk.examples.local_device import run as run_local_device

    return run_local_device()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ESP32 simulator using SmartHouse Device SDK")
    parser.add_argument("--house", default="home01")
    parser.add_argument("--device-id", default="device123")
    parser.add_argument("--mqtt-host", default="localhost")
    parser.add_argument("--mqtt-port", type=int, default=8883)
    parser.add_argument("--ca-cert", default="certs/ca.crt")
    parser.add_argument("--client-cert", default="certs/esp32-simulator.crt")
    parser.add_argument("--client-key", default="certs/esp32-simulator.key")
    parser.add_argument("--interval-seconds", type=float, default=3.0)
    parser.add_argument("--max-iterations", type=int, default=3)
    parser.add_argument("--registry-url", default="http://localhost:8081")
    parser.add_argument("--registry-token", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    # Reuse the SDK local device runtime so legacy simulator users get modern behavior.
    translated_argv = [
        "local_device.py",
        "--target",
        "esp32",
        "--house",
        args.house,
        "--device-id",
        args.device_id,
        "--mqtt-host",
        args.mqtt_host,
        "--mqtt-port",
        str(args.mqtt_port),
        "--ca-cert",
        args.ca_cert,
        "--client-cert",
        args.client_cert,
        "--client-key",
        args.client_key,
        "--interval-seconds",
        str(args.interval_seconds),
        "--max-iterations",
        str(args.max_iterations),
    ]
    if args.registry_token:
        translated_argv.extend(["--registry-url", args.registry_url, "--registry-token", args.registry_token])

    original_argv = sys.argv
    try:
        sys.argv = translated_argv
        return _run_sdk_local_device()
    finally:
        sys.argv = original_argv


if __name__ == "__main__":
    raise SystemExit(main())
