import argparse
import json
from urllib import request

from device_sdk.core.auth import AuthTokenRequest, ProvisioningAuthClient
from device_sdk.core.models import DeviceDescriptor
from device_sdk.core.registry import DeviceRegistryClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap-register a device via provisioning-key auth")
    parser.add_argument("--registry-url", default="http://localhost:8081")
    parser.add_argument("--provisioning-key", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--house", default="home01")
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--device-type", default="relay_module")
    parser.add_argument("--protocol", default="wifi")
    parser.add_argument("--capabilities", default="relay_output")
    parser.add_argument("--token-role", default="provisioner")
    parser.add_argument("--token-scopes", default="device:register")
    parser.add_argument("--token-expires-minutes", type=int, default=15)
    parser.add_argument("--require-lookup", action="store_true")
    return parser.parse_args()


def run() -> int:
    args = parse_args()
    capabilities = [c.strip() for c in args.capabilities.split(",") if c.strip()]
    scopes = [s.strip() for s in args.token_scopes.split(",") if s.strip()]

    auth_client = ProvisioningAuthClient(base_url=args.registry_url, provisioning_key=args.provisioning_key)
    token_response = auth_client.issue_token(
        AuthTokenRequest(
            subject=args.subject,
            role=args.token_role,
            house=args.house,
            scopes=scopes,
            expires_minutes=args.token_expires_minutes,
        )
    )
    if token_response.status_code != 200 or not token_response.access_token:
        raise RuntimeError(f"Token issue failed: {token_response.status_code} {token_response.body}")

    registry_client = DeviceRegistryClient(base_url=args.registry_url, bearer_token=token_response.access_token)
    register_response = registry_client.register_device(
        DeviceDescriptor(
            id=args.device_id,
            house=args.house,
            type=args.device_type,
            protocol=args.protocol,
            capabilities=capabilities,
        )
    )
    if register_response.status_code != 200:
        raise RuntimeError(
            f"Device registration failed: {register_response.status_code} {register_response.body}"
        )

    output = {
        "token_status": token_response.status_code,
        "register_status": register_response.status_code,
        "device_id": args.device_id,
    }

    if args.require_lookup:
        with request.urlopen(f"{args.registry_url}/devices/{args.device_id}", timeout=10.0) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        if body.get("id") != args.device_id:
            raise RuntimeError(f"Lookup mismatch: {body}")
        output["lookup_status"] = 200

    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
