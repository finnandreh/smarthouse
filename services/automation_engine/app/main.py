import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set

import paho.mqtt.client as mqtt
import psycopg
import yaml
from fastapi import FastAPI, Header, HTTPException, Request
import jwt


app = FastAPI(title="SmartHouse Automation Engine", version="0.1.0")

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MQTT_TLS_ENABLED = os.getenv("MQTT_TLS_ENABLED", "false").lower() == "true"
MQTT_TLS_CA_CERT = os.getenv("MQTT_TLS_CA_CERT", "")
MQTT_TLS_CLIENT_CERT = os.getenv("MQTT_TLS_CLIENT_CERT", "")
MQTT_TLS_CLIENT_KEY = os.getenv("MQTT_TLS_CLIENT_KEY", "")
RULES_PATH = os.getenv("RULES_PATH", "/app/config/rules.yaml")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://smarthouse:smarthouse@localhost:5432/smarthouse")
IDEMPOTENCY_WINDOW_SECONDS = int(os.getenv("IDEMPOTENCY_WINDOW_SECONDS", "5"))
JWT_SECRET = os.getenv("JWT_SECRET", "smarthouse-jwt-local-dev-secret")
JWT_PREVIOUS_SECRET = os.getenv("JWT_PREVIOUS_SECRET", "")
JWT_ISSUER = os.getenv("JWT_ISSUER", "smarthouse-device-registry")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "smarthouse-services")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACTIVE_KID = os.getenv("JWT_ACTIVE_KID", "k1")
JWT_PREVIOUS_KID = os.getenv("JWT_PREVIOUS_KID", "")
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", "60"))
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("AUTH_RATE_LIMIT_MAX_REQUESTS", "30"))

SERVICE_NAME = "automation-engine"
RELOAD_ALLOWED_ROLES: Set[str] = {"admin", "automation-admin"}

_mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="automation-engine")
_rules: List[Dict[str, Any]] = []
_recent_event_signatures: Dict[str, float] = {}
_rules_lock = threading.Lock()
_auth_rate_lock = threading.Lock()
_auth_rate_state: Dict[str, List[float]] = {}


def _load_rules(path: str) -> List[Dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return []

    with file_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return data.get("rules", [])


def _get_conn() -> psycopg.Connection:
    return psycopg.connect(DATABASE_URL, autocommit=True)


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


def _log_event(house: str, device_id: str, payload: Dict[str, Any]):
    event_type = str(payload.get("event", "unknown"))
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO automation_events (house, device_id, event_type, payload)
                VALUES (%s, %s, %s, %s::jsonb)
                """,
                (house, device_id, event_type, json.dumps(payload)),
            )


def _log_action(house: str, device_id: str, action: Dict[str, Any]):
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO automation_actions (house, device_id, action)
                VALUES (%s, %s, %s::jsonb)
                """,
                (house, device_id, json.dumps(action)),
            )


def _log_dead_letter(topic: str, raw_payload: str, reason: str):
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO automation_dead_letters (topic, raw_payload, reason)
                VALUES (%s, %s, %s)
                """,
                (topic, raw_payload, reason),
            )


def _is_duplicate_event(topic: str, payload: Dict[str, Any]) -> bool:
    signature = f"{topic}:{json.dumps(payload, sort_keys=True)}"
    now = time.time()
    cutoff = now - IDEMPOTENCY_WINDOW_SECONDS

    # Opportunistic cleanup to keep the in-memory map bounded.
    stale_keys = [key for key, ts in _recent_event_signatures.items() if ts < cutoff]
    for key in stale_keys:
        _recent_event_signatures.pop(key, None)

    last_seen = _recent_event_signatures.get(signature)
    if last_seen is not None and last_seen >= cutoff:
        return True

    _recent_event_signatures[signature] = now
    return False


def _condition_matches(conditions: Dict[str, Any], payload: Dict[str, Any]) -> bool:
    required_event = conditions.get("event")
    if required_event and payload.get("event") != required_event:
        return False

    # Placeholder for time/sun-state integration; defaults true for scaffold.
    after_sunset = conditions.get("after_sunset")
    if after_sunset is True:
        return True

    return True


def _execute_actions(house: str, device_id: str, actions: List[Dict[str, Any]]):
    for action in actions:
        control_topic = f"platform/{house}/{device_id}/control"
        _mqtt_client.publish(control_topic, json.dumps(action), qos=1)
        _log_action(house, device_id, action)


def _evaluate_rules(topic: str, payload: Dict[str, Any]):
    parts = topic.split("/")
    if len(parts) != 4:
        return

    _, house, device_id, kind = parts
    if kind != "event":
        return

    _log_event(house, device_id, payload)

    with _rules_lock:
        rules_snapshot = list(_rules)

    for rule in rules_snapshot:
        trigger = rule.get("trigger", {})
        match_event = trigger.get("event")
        if match_event and payload.get("event") != match_event:
            continue

        if not _condition_matches(rule.get("conditions", {}), payload):
            continue

        _execute_actions(house, device_id, rule.get("actions", []))


def _on_connect(client, userdata, flags, reason_code, properties):
    client.subscribe("platform/+/+/event")


def _on_message(client, userdata, msg):
    raw_payload = msg.payload.decode("utf-8", errors="replace")
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        _log_dead_letter(msg.topic, raw_payload, "invalid_json")
        return

    if _is_duplicate_event(msg.topic, payload):
        return

    _evaluate_rules(msg.topic, payload)


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
        claims = jwt.decode(
            token,
            secret,
            algorithms=[JWT_ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
        )
        if datetime.fromtimestamp(claims["exp"], tz=timezone.utc) <= datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Expired token")
        return claims
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


def _require_scope_claims(claims: dict, required_scope: str, allowed_roles: Set[str] | None = None):
    role = claims.get("role", "")
    scopes = claims.get("scopes", [])
    if allowed_roles and role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Role not permitted")
    if required_scope not in scopes and role != "admin":
        raise HTTPException(status_code=403, detail="Missing required scope")


@app.on_event("startup")
def startup_event():
    global _rules
    _ensure_auth_security_schema()
    _ensure_revoked_tokens_schema()
    with _rules_lock:
        _rules = _load_rules(RULES_PATH)

    thread = threading.Thread(target=_mqtt_loop, daemon=True)
    thread.start()


@app.get("/health")
def health():
    return {"status": "ok", "loaded_rules": len(_rules)}


@app.get("/rules")
def rules():
    with _rules_lock:
        return {"rules": list(_rules)}


@app.post("/rules/reload")
def reload_rules(request_meta: Request, authorization: str | None = Header(default=None)):
    endpoint = "/rules/reload"
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
        _require_scope_claims(claims, required_scope="rules:reload", allowed_roles=RELOAD_ALLOWED_ROLES)
    except HTTPException as exc:
        _log_auth_security_event(endpoint, client_ip, "denied", str(exc.detail))
        raise

    global _rules
    with _rules_lock:
        _rules = _load_rules(RULES_PATH)
        _log_auth_security_event(endpoint, client_ip, "allowed", "rules_reloaded", subject=claims.get("sub"))
        return {"reloaded": True, "loaded_rules": len(_rules)}
