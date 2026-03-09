import json
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Set
from uuid import uuid4

import paho.mqtt.client as mqtt
import jwt
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field
import psycopg


class DeviceRegistration(BaseModel):
    id: str = Field(min_length=1)
    house: str = Field(min_length=1)
    type: str = Field(min_length=1)
    protocol: str = Field(min_length=1)
    capabilities: List[str] = Field(default_factory=list)


class TokenRequest(BaseModel):
    subject: str = Field(min_length=1)
    role: str = Field(min_length=1)
    house: str = Field(min_length=1)
    scopes: List[str] = Field(default_factory=list)
    expires_minutes: int = Field(default=30, ge=1, le=1440)


class TokenRevocationRequest(BaseModel):
    token: str = Field(min_length=1)


app = FastAPI(title="SmartHouse Device Registry", version="0.1.0")

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MQTT_TLS_ENABLED = os.getenv("MQTT_TLS_ENABLED", "false").lower() == "true"
MQTT_TLS_CA_CERT = os.getenv("MQTT_TLS_CA_CERT", "")
MQTT_TLS_CLIENT_CERT = os.getenv("MQTT_TLS_CLIENT_CERT", "")
MQTT_TLS_CLIENT_KEY = os.getenv("MQTT_TLS_CLIENT_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://smarthouse:smarthouse@localhost:5432/smarthouse")
PROVISIONING_MASTER_KEY = os.getenv("PROVISIONING_MASTER_KEY", "changeme-provisioning-local-dev")
JWT_SECRET = os.getenv("JWT_SECRET", "smarthouse-jwt-local-dev-secret")
JWT_PREVIOUS_SECRET = os.getenv("JWT_PREVIOUS_SECRET", "")
JWT_ISSUER = os.getenv("JWT_ISSUER", "smarthouse-device-registry")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "smarthouse-services")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACTIVE_KID = os.getenv("JWT_ACTIVE_KID", "k1")
JWT_PREVIOUS_KID = os.getenv("JWT_PREVIOUS_KID", "")
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", "60"))
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("AUTH_RATE_LIMIT_MAX_REQUESTS", "30"))

SERVICE_NAME = "device-registry"
ALLOWED_TOKEN_ROLES: Set[str] = {"admin", "operator", "provisioner", "automation-admin"}
ALLOWED_TOKEN_SCOPES: Set[str] = {"device:register", "rules:reload"}
ROLE_SCOPE_POLICY: Dict[str, Set[str]] = {
    "admin": {"device:register", "rules:reload"},
    "operator": {"device:register"},
    "provisioner": {"device:register"},
    "automation-admin": {"rules:reload"},
}

_mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="device-registry")
_auth_rate_lock = threading.Lock()
_auth_rate_state: Dict[str, List[float]] = {}


def _get_conn() -> psycopg.Connection:
    return psycopg.connect(DATABASE_URL, autocommit=True)


def _upsert_device(device: DeviceRegistration):
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO devices (id, house, type, protocol, capabilities, updated_at)
                VALUES (%s, %s, %s, %s, %s::jsonb, NOW())
                ON CONFLICT (id)
                DO UPDATE SET
                  house = EXCLUDED.house,
                  type = EXCLUDED.type,
                  protocol = EXCLUDED.protocol,
                  capabilities = EXCLUDED.capabilities,
                  updated_at = NOW()
                """,
                (
                    device.id,
                    device.house,
                    device.type,
                    device.protocol,
                    json.dumps(device.capabilities),
                ),
            )


def _insert_registry_event(device: DeviceRegistration, event_type: str, payload: dict):
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO registry_events (device_id, house, event_type, payload)
                VALUES (%s, %s, %s, %s::jsonb)
                """,
                (device.id, device.house, event_type, json.dumps(payload)),
            )


def _insert_provisioning_audit(subject: str, house: str, role: str, scopes: List[str], issued_by: str):
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO provisioning_audit (subject, house, role, scopes, issued_by)
                VALUES (%s, %s, %s, %s::jsonb, %s)
                """,
                (subject, house, role, json.dumps(scopes), issued_by),
            )


def _ensure_provisioning_schema():
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS provisioning_audit (
                  audit_id BIGSERIAL PRIMARY KEY,
                  subject TEXT NOT NULL,
                  house TEXT NOT NULL,
                  role TEXT NOT NULL,
                  scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
                  issued_by TEXT NOT NULL,
                  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )


def _ensure_auth_security_schema():
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_security_events (
                  event_id BIGSERIAL PRIMARY KEY,
                  service_name TEXT NOT NULL,
                  endpoint TEXT NOT NULL,
                  client_ip TEXT NOT NULL,
                  subject TEXT,
                  outcome TEXT NOT NULL,
                  reason TEXT NOT NULL,
                  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )


def _ensure_revoked_tokens_schema():
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS revoked_tokens (
                  jti TEXT PRIMARY KEY,
                  subject TEXT,
                  revoked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                  expires_at TIMESTAMPTZ NOT NULL
                )
                """
            )


def _active_jwt_keys() -> Dict[str, str]:
    keys: Dict[str, str] = {JWT_ACTIVE_KID: JWT_SECRET}
    if JWT_PREVIOUS_KID and JWT_PREVIOUS_SECRET:
        keys[JWT_PREVIOUS_KID] = JWT_PREVIOUS_SECRET
    return keys


def _resolve_jwt_secret_for_token(token: str) -> str:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid token header") from exc

    kid = header.get("kid")
    keys = _active_jwt_keys()
    if not kid or kid not in keys:
        raise HTTPException(status_code=401, detail="Unknown token key id")

    return keys[kid]


def _is_token_revoked(jti: str) -> bool:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM revoked_tokens WHERE jti = %s LIMIT 1", (jti,))
            return cur.fetchone() is not None


def _revoke_token_jti(jti: str, subject: str | None, expires_at_epoch: int):
    expires_at = datetime.fromtimestamp(expires_at_epoch, tz=timezone.utc)
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO revoked_tokens (jti, subject, expires_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (jti)
                DO UPDATE SET
                  subject = EXCLUDED.subject,
                  expires_at = EXCLUDED.expires_at
                """,
                (jti, subject, expires_at),
            )


def _log_auth_security_event(
    endpoint: str,
    client_ip: str,
    outcome: str,
    reason: str,
    subject: str | None = None,
    metadata: dict | None = None,
):
    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO auth_security_events (service_name, endpoint, client_ip, subject, outcome, reason, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        SERVICE_NAME,
                        endpoint,
                        client_ip,
                        subject,
                        outcome,
                        reason,
                        json.dumps(metadata or {}),
                    ),
                )
    except Exception:
        # Auth path should not fail closed if audit logging write fails.
        pass


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _enforce_auth_rate_limit(client_ip: str, endpoint: str):
    bucket_key = f"{client_ip}:{endpoint}"
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS

    with _auth_rate_lock:
        recent = [ts for ts in _auth_rate_state.get(bucket_key, []) if ts >= cutoff]
        if len(recent) >= RATE_LIMIT_MAX_REQUESTS:
            _auth_rate_state[bucket_key] = recent
            raise HTTPException(status_code=429, detail="Too Many Requests")
        recent.append(now)
        _auth_rate_state[bucket_key] = recent


def _on_connect(client, userdata, flags, reason_code, properties):
    client.subscribe("platform/+/+/event")


def _on_message(client, userdata, msg):
    topic_parts = msg.topic.split("/")
    if len(topic_parts) != 4:
        return

    _, house, device_id, kind = topic_parts
    if kind != "event":
        return

    # Auto-register devices announcing themselves via event payload.
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except json.JSONDecodeError:
        return

    if payload.get("event") != "device_announce":
        return

    entry = DeviceRegistration(
        id=device_id,
        house=house,
        type=str(payload.get("type", "unknown")),
        protocol=str(payload.get("protocol", "unknown")),
        capabilities=payload.get("capabilities", []),
    )
    _upsert_device(entry)
    _insert_registry_event(entry, "device_announce", payload)


def _mqtt_loop():
    _mqtt_client.on_connect = _on_connect
    _mqtt_client.on_message = _on_message
    if MQTT_USERNAME:
        _mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    if MQTT_TLS_ENABLED:
        _mqtt_client.tls_set(
            ca_certs=MQTT_TLS_CA_CERT,
            certfile=MQTT_TLS_CLIENT_CERT,
            keyfile=MQTT_TLS_CLIENT_KEY,
        )
    _mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    _mqtt_client.loop_forever()


def _create_access_token(request: TokenRequest) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": request.subject,
        "role": request.role,
        "house": request.house,
        "scopes": request.scopes,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=request.expires_minutes)).timestamp()),
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM, headers={"kid": JWT_ACTIVE_KID})


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    return token


def _decode_token(token: str) -> dict:
    try:
        secret = _resolve_jwt_secret_for_token(token)
        return jwt.decode(
            token,
            secret,
            algorithms=[JWT_ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


def _require_scope_claims(claims: dict, required_scope: str, required_house: str | None = None):
    scopes = claims.get("scopes", [])
    role = claims.get("role", "")
    token_house = claims.get("house", "")

    if required_scope not in scopes and role != "admin":
        raise HTTPException(status_code=403, detail="Missing required scope")
    if required_house and token_house != required_house and role != "admin":
        raise HTTPException(status_code=403, detail="House scope mismatch")


def _validate_token_request(request: TokenRequest):
    if request.role not in ALLOWED_TOKEN_ROLES:
        raise HTTPException(status_code=400, detail="Unsupported role")

    invalid_scopes = [scope for scope in request.scopes if scope not in ALLOWED_TOKEN_SCOPES]
    if invalid_scopes:
        raise HTTPException(status_code=400, detail=f"Unsupported scopes: {','.join(invalid_scopes)}")

    role_allowed_scopes = ROLE_SCOPE_POLICY.get(request.role, set())
    forbidden_for_role = [scope for scope in request.scopes if scope not in role_allowed_scopes]
    if forbidden_for_role:
        raise HTTPException(status_code=400, detail=f"Role-scope mismatch: {','.join(forbidden_for_role)}")


def _require_provisioning_key(x_provisioning_key: str | None):
    if x_provisioning_key != PROVISIONING_MASTER_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.on_event("startup")
def startup_event():
    _ensure_provisioning_schema()
    _ensure_auth_security_schema()
    _ensure_revoked_tokens_schema()
    thread = threading.Thread(target=_mqtt_loop, daemon=True)
    thread.start()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/token")
def issue_token(request: TokenRequest, request_meta: Request, x_provisioning_key: str | None = Header(default=None)):
    endpoint = "/auth/token"
    client_ip = _client_ip(request_meta)

    try:
        _enforce_auth_rate_limit(client_ip, endpoint)
    except HTTPException as exc:
        _log_auth_security_event(endpoint, client_ip, "denied", "rate_limited")
        raise exc

    try:
        _require_provisioning_key(x_provisioning_key)
        _validate_token_request(request)
        access_token = _create_access_token(request)
    except HTTPException as exc:
        _log_auth_security_event(endpoint, client_ip, "denied", str(exc.detail))
        raise

    _insert_provisioning_audit(
        subject=request.subject,
        house=request.house,
        role=request.role,
        scopes=request.scopes,
        issued_by="provisioning-key",
    )
    _log_auth_security_event(endpoint, client_ip, "allowed", "token_issued", subject=request.subject)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_minutes": request.expires_minutes,
        "kid": JWT_ACTIVE_KID,
    }


@app.post("/auth/revoke")
def revoke_token(
    request: TokenRevocationRequest,
    request_meta: Request,
    authorization: str | None = Header(default=None),
):
    endpoint = "/auth/revoke"
    client_ip = _client_ip(request_meta)

    try:
        _enforce_auth_rate_limit(client_ip, endpoint)
    except HTTPException as exc:
        _log_auth_security_event(endpoint, client_ip, "denied", "rate_limited")
        raise exc

    try:
        caller_token = _extract_bearer_token(authorization)
        caller_claims = _decode_token(caller_token)
        _require_scope_claims(caller_claims, required_scope="rules:reload")

        target_claims = _decode_token(request.token)
        jti = target_claims.get("jti")
        exp = target_claims.get("exp")
        if not jti or not exp:
            raise HTTPException(status_code=400, detail="Token missing jti/exp")

        _revoke_token_jti(jti, target_claims.get("sub"), int(exp))
    except HTTPException as exc:
        _log_auth_security_event(endpoint, client_ip, "denied", str(exc.detail))
        raise

    _log_auth_security_event(endpoint, client_ip, "allowed", "token_revoked", subject=caller_claims.get("sub"))
    return {"revoked": True, "jti": jti}


@app.get("/devices")
def list_devices():
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, house, type, protocol, capabilities FROM devices ORDER BY id")
            rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "house": row[1],
            "type": row[2],
            "protocol": row[3],
            "capabilities": row[4],
        }
        for row in rows
    ]


@app.get("/devices/{device_id}")
def get_device(device_id: str):
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, house, type, protocol, capabilities FROM devices WHERE id = %s",
                (device_id,),
            )
            row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Device not found")

    return {
        "id": row[0],
        "house": row[1],
        "type": row[2],
        "protocol": row[3],
        "capabilities": row[4],
    }


@app.post("/devices/register")
def register_device(device: DeviceRegistration, request_meta: Request, authorization: str | None = Header(default=None)):
    endpoint = "/devices/register"
    client_ip = _client_ip(request_meta)

    try:
        _enforce_auth_rate_limit(client_ip, endpoint)
    except HTTPException as exc:
        _log_auth_security_event(endpoint, client_ip, "denied", "rate_limited")
        raise exc

    try:
        token = _extract_bearer_token(authorization)
        claims = _decode_token(token)
        jti = claims.get("jti")
        if not jti:
            raise HTTPException(status_code=401, detail="Token missing jti")
        if _is_token_revoked(str(jti)):
            raise HTTPException(status_code=401, detail="Token revoked")
        _require_scope_claims(claims, required_scope="device:register", required_house=device.house)
    except HTTPException as exc:
        _log_auth_security_event(endpoint, client_ip, "denied", str(exc.detail))
        raise

    _upsert_device(device)
    _insert_registry_event(device, "device_registered", device.model_dump())
    _log_auth_security_event(endpoint, client_ip, "allowed", "device_registered", subject=claims.get("sub"))

    event_topic = f"platform/{device.house}/{device.id}/event"
    event_payload = {
        "event": "device_registered",
        "device": device.model_dump(),
    }
    _mqtt_client.publish(event_topic, json.dumps(event_payload), qos=1)
    return {"registered": True, "device": device.model_dump()}
