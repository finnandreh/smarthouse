import json
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib import request
from urllib.error import HTTPError, URLError


@dataclass(frozen=True)
class AuthTokenRequest:
    subject: str
    role: str
    house: str
    scopes: List[str]
    expires_minutes: int = 30


@dataclass(frozen=True)
class AuthTokenResponse:
    status_code: int
    body: Dict[str, object]

    @property
    def access_token(self) -> str:
        token = self.body.get("access_token", "")
        return str(token) if token else ""


class ProvisioningAuthClient:
    """HTTP helper for provisioning-key based token issuance."""

    def __init__(
        self,
        base_url: str,
        provisioning_key: str,
        timeout_seconds: float = 10.0,
        max_retries: int = 1,
        retry_backoff_seconds: float = 0.5,
    ):
        self.base_url = base_url.rstrip("/")
        self.provisioning_key = provisioning_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, max_retries)
        self.retry_backoff_seconds = max(0.0, retry_backoff_seconds)

    def issue_token(self, token_request: AuthTokenRequest) -> AuthTokenResponse:
        endpoint = f"{self.base_url}/auth/token"
        payload = json.dumps(
            {
                "subject": token_request.subject,
                "role": token_request.role,
                "house": token_request.house,
                "scopes": token_request.scopes,
                "expires_minutes": token_request.expires_minutes,
            }
        ).encode("utf-8")

        req = request.Request(
            endpoint,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "x-provisioning-key": self.provisioning_key,
            },
        )

        network_error: Optional[str] = None
        for attempt in range(self.max_retries + 1):
            try:
                with request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                    return AuthTokenResponse(status_code=resp.status, body=body)
            except HTTPError as exc:
                detail = exc.read().decode("utf-8")
                try:
                    parsed = json.loads(detail)
                except json.JSONDecodeError:
                    parsed = {"detail": detail or exc.reason}
                return AuthTokenResponse(status_code=exc.code, body=parsed)
            except (URLError, TimeoutError) as exc:
                network_error = str(exc.reason) if isinstance(exc, URLError) and exc.reason else str(exc)
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff_seconds)

        return AuthTokenResponse(
            status_code=0,
            body={"detail": f"Auth endpoint unreachable: {network_error or 'unknown network error'}"},
        )
