import json
import time
from dataclasses import dataclass
from typing import Dict, Optional
from urllib import request
from urllib.error import HTTPError, URLError

from .models import DeviceDescriptor


@dataclass(frozen=True)
class RegistryResponse:
    status_code: int
    body: Dict[str, object]


class DeviceRegistryClient:
    """HTTP helper for device registration against the local registry service."""

    def __init__(
        self,
        base_url: str,
        bearer_token: str,
        timeout_seconds: float = 10.0,
        max_retries: int = 1,
        retry_backoff_seconds: float = 0.5,
    ):
        self.base_url = base_url.rstrip("/")
        self.bearer_token = bearer_token
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, max_retries)
        self.retry_backoff_seconds = max(0.0, retry_backoff_seconds)

    def register_device(self, device: DeviceDescriptor) -> RegistryResponse:
        endpoint = f"{self.base_url}/devices/register"
        payload = json.dumps(device.to_registry_payload()).encode("utf-8")
        req = request.Request(
            endpoint,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.bearer_token}",
            },
        )

        network_error: Optional[str] = None
        for attempt in range(self.max_retries + 1):
            try:
                with request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                    return RegistryResponse(status_code=resp.status, body=body)
            except HTTPError as exc:
                detail = exc.read().decode("utf-8")
                try:
                    parsed = json.loads(detail)
                except json.JSONDecodeError:
                    parsed = {"detail": detail or exc.reason}
                return RegistryResponse(status_code=exc.code, body=parsed)
            except (URLError, TimeoutError) as exc:
                network_error = str(exc.reason) if isinstance(exc, URLError) and exc.reason else str(exc)
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff_seconds)

        return RegistryResponse(
            status_code=0,
            body={"detail": f"Registry unreachable: {network_error or 'unknown network error'}"},
        )
