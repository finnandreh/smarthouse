import json
import os
import time
import hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Set, Tuple
from uuid import uuid4

import psycopg
import requests
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field


class EdgeConfig(BaseModel):
    site_id: str = Field(default="home01", min_length=1)
    site_name: str = Field(default="SmartHouse Site", min_length=1)
    enabled_bridges: List[str] = Field(default_factory=lambda: ["modbus", "knx", "bacnet"])


class DeviceProvisionRequest(BaseModel):
    id: str = Field(min_length=1)
    house: str = Field(min_length=1)
    type: str = Field(min_length=1)
    protocol: str = Field(min_length=1)
    capabilities: List[str] = Field(default_factory=list)


class DesiredState(BaseModel):
    site_id: str = Field(default="home01", min_length=1)
    enabled_bridges: List[str] = Field(default_factory=lambda: ["modbus", "knx", "bacnet"])
    automation_enabled: bool = True
    provisioning_enabled: bool = True


class ProvisionSessionPrepareRequest(DeviceProvisionRequest):
    installer_id: str = Field(default="edge-installer", min_length=1)


class MaintenanceRequest(BaseModel):
    reason: str = Field(default="scheduled_maintenance", min_length=1)


app = FastAPI(title="SmartHouse Edge Controller", version="0.1.0")

DEVICE_REGISTRY_URL = os.getenv("DEVICE_REGISTRY_URL", "http://device-registry:8081")
AUTOMATION_ENGINE_URL = os.getenv("AUTOMATION_ENGINE_URL", "http://automation-engine:8082")
BRIDGE_MODBUS_URL = os.getenv("BRIDGE_MODBUS_URL", "http://bridge-modbus:8091")
BRIDGE_KNX_URL = os.getenv("BRIDGE_KNX_URL", "http://bridge-knx:8092")
BRIDGE_BACNET_URL = os.getenv("BRIDGE_BACNET_URL", "http://bridge-bacnet:8093")
PROVISIONING_MASTER_KEY = os.getenv("PROVISIONING_MASTER_KEY", "changeme-provisioning-local-dev")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://smarthouse:smarthouse@postgres:5432/smarthouse")
EDGE_API_KEY = os.getenv("EDGE_API_KEY", "changeme-edge-local-dev")
EDGE_API_KEY_ADMIN = os.getenv("EDGE_API_KEY_ADMIN", EDGE_API_KEY)
EDGE_API_KEY_OPERATOR = os.getenv("EDGE_API_KEY_OPERATOR", "changeme-edge-operator-local-dev")
HTTP_TIMEOUT_SECONDS = float(os.getenv("EDGE_HTTP_TIMEOUT_SECONDS", "5"))
EDGE_CONFIG_PATH = Path(os.getenv("EDGE_CONFIG_PATH", "/app/config/edge_config.json"))
RECONCILE_SLO_WINDOW_MINUTES = int(os.getenv("RECONCILE_SLO_WINDOW_MINUTES", "60"))
RECONCILE_SLO_MAX_DRIFT_RATIO = float(os.getenv("RECONCILE_SLO_MAX_DRIFT_RATIO", "0.10"))
RECONCILE_SLO_MIN_EVENTS = int(os.getenv("RECONCILE_SLO_MIN_EVENTS", "5"))
BRIDGE_URLS: Dict[str, str] = {
    "modbus": BRIDGE_MODBUS_URL,
    "knx": BRIDGE_KNX_URL,
    "bacnet": BRIDGE_BACNET_URL,
}

ADMIN_SCOPES: Set[str] = {
    "edge:config:read",
    "edge:config:write",
    "edge:provision",
    "edge:provision:session",
    "edge:lifecycle:reload",
    "edge:lifecycle:bridges",
    "edge:audit:read",
    "edge:state:read",
    "edge:state:write",
    "edge:state:reconcile",
    "edge:maintenance:read",
    "edge:maintenance:write",
}
OPERATOR_SCOPES: Set[str] = {
    "edge:config:read",
    "edge:provision",
    "edge:provision:session",
    "edge:lifecycle:bridges",
    "edge:maintenance:read",
    "edge:state:read",
}


def _get_conn() -> psycopg.Connection:
    return psycopg.connect(DATABASE_URL, autocommit=True)


def _ensure_edge_audit_schema():
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS edge_controller_audit (
                  audit_id BIGSERIAL PRIMARY KEY,
                  endpoint TEXT NOT NULL,
                  action TEXT NOT NULL,
                  actor TEXT,
                  scope TEXT,
                  outcome TEXT NOT NULL,
                  reason TEXT NOT NULL,
                  client_ip TEXT NOT NULL,
                  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )


def _ensure_edge_control_plane_schema():
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS edge_desired_state (
                    state_key TEXT PRIMARY KEY,
                    value JSONB NOT NULL,
                    updated_by TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS edge_reconciliation_events (
                    event_id BIGSERIAL PRIMARY KEY,
                    component TEXT NOT NULL,
                    desired_state JSONB NOT NULL,
                    actual_state JSONB NOT NULL,
                    outcome TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS edge_provisioning_sessions (
                    session_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    request JSONB NOT NULL,
                    validation JSONB NOT NULL DEFAULT '{}'::jsonb,
                    result JSONB NOT NULL DEFAULT '{}'::jsonb,
                    error TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS edge_maintenance_lock (
                    lock_name TEXT PRIMARY KEY,
                    enabled BOOLEAN NOT NULL DEFAULT FALSE,
                    reason TEXT NOT NULL DEFAULT 'none',
                    updated_by TEXT NOT NULL DEFAULT 'system',
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS edge_idempotency_keys (
                    endpoint TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    response JSONB,
                    status_code INTEGER,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (endpoint, idempotency_key)
                )
                """
            )
            cur.execute(
                """
                INSERT INTO edge_maintenance_lock (lock_name, enabled, reason, updated_by)
                VALUES ('global', FALSE, 'none', 'system')
                ON CONFLICT (lock_name) DO NOTHING
                """
            )


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log_edge_action(
    endpoint: str,
    action: str,
    actor: str | None,
    scope: str | None,
    outcome: str,
    reason: str,
    client_ip: str,
    metadata: dict | None = None,
):
    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO edge_controller_audit (endpoint, action, actor, scope, outcome, reason, client_ip, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        endpoint,
                        action,
                        actor,
                        scope,
                        outcome,
                        reason,
                        client_ip,
                        json.dumps(metadata or {}),
                    ),
                )
    except Exception:
        pass


def _authenticate_edge_key(x_edge_api_key: str | None) -> Tuple[str, Set[str]]:
    if x_edge_api_key == EDGE_API_KEY_ADMIN:
        return "edge-admin", ADMIN_SCOPES
    if x_edge_api_key == EDGE_API_KEY_OPERATOR:
        return "edge-operator", OPERATOR_SCOPES
    raise HTTPException(status_code=401, detail="Unauthorized")


def _authorize_scope(
    required_scope: str,
    x_edge_api_key: str | None,
    request: Request,
    endpoint: str,
    action: str,
    metadata: dict | None = None,
) -> str:
    client_ip = _client_ip(request)
    try:
        actor, scopes = _authenticate_edge_key(x_edge_api_key)
    except HTTPException as exc:
        _log_edge_action(endpoint, action, None, required_scope, "denied", str(exc.detail), client_ip, metadata)
        raise

    if required_scope not in scopes:
        _log_edge_action(endpoint, action, actor, required_scope, "denied", "Missing scope", client_ip, metadata)
        raise HTTPException(status_code=403, detail="Forbidden")

    return actor


def _maintenance_status() -> Dict[str, Any]:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT enabled, reason, updated_by, updated_at
                FROM edge_maintenance_lock
                WHERE lock_name = 'global'
                """
            )
            row = cur.fetchone()

    if row is None:
        return {
            "enabled": False,
            "reason": "none",
            "updated_by": "system",
            "updated_at": None,
        }

    return {
        "enabled": bool(row[0]),
        "reason": row[1],
        "updated_by": row[2],
        "updated_at": row[3].isoformat() if row[3] else None,
    }


def _set_maintenance(enabled: bool, reason: str, actor: str):
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE edge_maintenance_lock
                SET enabled = %s, reason = %s, updated_by = %s, updated_at = NOW()
                WHERE lock_name = 'global'
                """,
                (enabled, reason, actor),
            )


def _require_not_in_maintenance():
    status = _maintenance_status()
    if status["enabled"]:
        raise HTTPException(status_code=423, detail=f"Maintenance mode enabled: {status['reason']}")


def _load_config() -> EdgeConfig:
    if not EDGE_CONFIG_PATH.exists():
        config = EdgeConfig()
        _save_config(config)
        return config

    with EDGE_CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return EdgeConfig(**data)


def _save_config(config: EdgeConfig):
    EDGE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EDGE_CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(config.model_dump(), f, indent=2)


def _service_health(url: str) -> Dict[str, Any]:
    try:
        response = requests.get(f"{url}/health", timeout=HTTP_TIMEOUT_SECONDS)
        return {
            "ok": response.status_code == 200,
            "status_code": response.status_code,
            "body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
        }
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)}


def _request_payload_hash(payload: dict | None) -> str:
    canonical = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _load_idempotent_result(endpoint: str, idempotency_key: str) -> Dict[str, Any] | None:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT request_hash, response, status_code
                FROM edge_idempotency_keys
                WHERE endpoint = %s AND idempotency_key = %s
                """,
                (endpoint, idempotency_key),
            )
            row = cur.fetchone()

    if row is None:
        return None
    return {
        "request_hash": row[0],
        "response": row[1],
        "status_code": row[2],
    }


def _save_idempotent_result(endpoint: str, idempotency_key: str, request_hash: str, response: dict, status_code: int):
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO edge_idempotency_keys (endpoint, idempotency_key, request_hash, response, status_code, updated_at)
                VALUES (%s, %s, %s, %s::jsonb, %s, NOW())
                ON CONFLICT (endpoint, idempotency_key)
                DO UPDATE SET
                  request_hash = EXCLUDED.request_hash,
                  response = EXCLUDED.response,
                  status_code = EXCLUDED.status_code,
                  updated_at = NOW()
                """,
                (endpoint, idempotency_key, request_hash, json.dumps(response), status_code),
            )


def _execute_idempotent(endpoint: str, idempotency_key: str | None, request_payload: dict | None, execute_fn):
    if not idempotency_key:
        return execute_fn()

    request_hash = _request_payload_hash(request_payload)
    existing = _load_idempotent_result(endpoint, idempotency_key)
    if existing is not None:
        if existing["request_hash"] != request_hash:
            raise HTTPException(status_code=409, detail="Idempotency key already used with different payload")
        if existing["response"] is None:
            raise HTTPException(status_code=409, detail="Idempotent request still in progress")
        return existing["response"]

    result = execute_fn()
    if isinstance(result, dict):
        _save_idempotent_result(endpoint, idempotency_key, request_hash, result, 200)
    return result


def _bridge_lifecycle_command(bridge: str, command: str) -> Dict[str, Any]:
    if bridge not in BRIDGE_URLS:
        raise HTTPException(status_code=404, detail=f"Unknown bridge: {bridge}")
    if command not in ("reload", "restart"):
        raise HTTPException(status_code=400, detail=f"Unsupported command: {command}")

    desired = _load_desired_state()
    if bridge not in desired.enabled_bridges:
        raise HTTPException(status_code=409, detail=f"Bridge disabled by desired state: {bridge}")

    url = BRIDGE_URLS[bridge]
    response = None
    last_error: str | None = None
    for _ in range(3):
        try:
            response = requests.post(f"{url}/lifecycle/{command}", timeout=HTTP_TIMEOUT_SECONDS)
            if response.status_code == 200:
                break
            last_error = f"status={response.status_code} body={response.text}"
        except requests.RequestException as exc:
            last_error = str(exc)
        time.sleep(0.3)

    if response is None or response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Bridge command failed: {last_error or 'unknown error'}")

    response_body: Any
    if response.headers.get("content-type", "").startswith("application/json"):
        response_body = response.json()
    else:
        response_body = response.text

    return {
        "bridge": bridge,
        "command": command,
        "applied": True,
        "response": response_body,
    }


def _issue_token(subject: str, role: str, house: str, scopes: List[str], expires_minutes: int = 30) -> str:
    payload = {
        "subject": subject,
        "role": role,
        "house": house,
        "scopes": scopes,
        "expires_minutes": expires_minutes,
    }

    response = requests.post(
        f"{DEVICE_REGISTRY_URL}/auth/token",
        headers={
            "Content-Type": "application/json",
            "x-provisioning-key": PROVISIONING_MASTER_KEY,
        },
        json=payload,
        timeout=HTTP_TIMEOUT_SECONDS,
    )

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Token issue failed: {response.text}")

    token = response.json().get("access_token", "")
    if not token:
        raise HTTPException(status_code=502, detail="Token issue returned empty token")

    return token


@app.get("/health")
def health():
    return {"status": "ok", "component": "edge-controller"}


@app.get("/health/dependencies")
def dependency_health():
    services = {
        "device_registry": _service_health(DEVICE_REGISTRY_URL),
        "automation_engine": _service_health(AUTOMATION_ENGINE_URL),
        "bridge_modbus": _service_health(BRIDGE_MODBUS_URL),
        "bridge_knx": _service_health(BRIDGE_KNX_URL),
        "bridge_bacnet": _service_health(BRIDGE_BACNET_URL),
    }
    all_ok = all(item.get("ok", False) for item in services.values())
    return {"status": "ok" if all_ok else "degraded", "services": services}


def _default_desired_state() -> DesiredState:
    config = _load_config()
    return DesiredState(
        site_id=config.site_id,
        enabled_bridges=list(config.enabled_bridges),
        automation_enabled=True,
        provisioning_enabled=True,
    )


def _load_desired_state() -> DesiredState:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM edge_desired_state WHERE state_key = 'default'")
            row = cur.fetchone()

    if row is None:
        desired = _default_desired_state()
        _save_desired_state(desired, updated_by="system")
        return desired

    return DesiredState(**row[0])


def _save_desired_state(state: DesiredState, updated_by: str):
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO edge_desired_state (state_key, value, updated_by, updated_at)
                VALUES ('default', %s::jsonb, %s, NOW())
                ON CONFLICT (state_key)
                DO UPDATE SET
                  value = EXCLUDED.value,
                  updated_by = EXCLUDED.updated_by,
                  updated_at = NOW()
                """,
                (json.dumps(state.model_dump()), updated_by),
            )


def _record_reconciliation(
    component: str,
    desired_state: dict,
    actual_state: dict,
    outcome: str,
    reason: str,
    metadata: dict | None = None,
):
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO edge_reconciliation_events (component, desired_state, actual_state, outcome, reason, metadata)
                VALUES (%s, %s::jsonb, %s::jsonb, %s, %s, %s::jsonb)
                """,
                (
                    component,
                    json.dumps(desired_state),
                    json.dumps(actual_state),
                    outcome,
                    reason,
                    json.dumps(metadata or {}),
                ),
            )


def _reconcile_once() -> Dict[str, Any]:
    desired = _load_desired_state()
    deps = dependency_health()["services"]

    checks: List[Dict[str, Any]] = []

    automation_actual = deps["automation_engine"]
    automation_ok = automation_actual.get("ok", False) if desired.automation_enabled else True
    checks.append(
        {
            "component": "automation_engine",
            "desired": {"enabled": desired.automation_enabled},
            "actual": automation_actual,
            "ok": automation_ok,
            "reason": "health_check",
        }
    )

    bridge_map = {
        "modbus": "bridge_modbus",
        "knx": "bridge_knx",
        "bacnet": "bridge_bacnet",
    }
    for bridge in ("modbus", "knx", "bacnet"):
        key = bridge_map[bridge]
        enabled = bridge in desired.enabled_bridges
        actual = deps[key]
        ok = actual.get("ok", False) if enabled else True
        checks.append(
            {
                "component": key,
                "desired": {"enabled": enabled},
                "actual": actual,
                "ok": ok,
                "reason": "health_check",
            }
        )

    for item in checks:
        _record_reconciliation(
            component=item["component"],
            desired_state=item["desired"],
            actual_state=item["actual"],
            outcome="ok" if item["ok"] else "drift",
            reason=item["reason"],
            metadata={"reconciled_at": _utc_now_iso()},
        )

    overall_ok = all(item["ok"] for item in checks)
    return {
        "status": "ok" if overall_ok else "drift",
        "desired": desired.model_dump(),
        "checks": checks,
    }


def _reconcile_slo_metrics(window_minutes: int) -> Dict[str, Any]:
    effective_window = max(1, min(window_minutes, 24 * 60))
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=effective_window)

    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  COUNT(*) AS total,
                  COUNT(*) FILTER (WHERE outcome = 'drift') AS drift,
                  COUNT(*) FILTER (WHERE outcome = 'ok') AS ok
                FROM edge_reconciliation_events
                WHERE created_at >= %s
                """,
                (cutoff,),
            )
            summary = cur.fetchone()

            cur.execute(
                """
                SELECT component, outcome, COUNT(*)
                FROM edge_reconciliation_events
                WHERE created_at >= %s
                GROUP BY component, outcome
                ORDER BY component, outcome
                """,
                (cutoff,),
            )
            component_rows = cur.fetchall()

            cur.execute(
                """
                SELECT MAX(created_at)
                FROM edge_reconciliation_events
                """
            )
            last_any = cur.fetchone()

            cur.execute(
                """
                SELECT MAX(created_at)
                FROM edge_reconciliation_events
                WHERE outcome = 'drift'
                """
            )
            last_drift = cur.fetchone()

    total_events = int(summary[0] or 0)
    drift_events = int(summary[1] or 0)
    ok_events = int(summary[2] or 0)
    drift_ratio = (drift_events / total_events) if total_events > 0 else 0.0
    has_enough_data = total_events >= RECONCILE_SLO_MIN_EVENTS
    slo_violated = bool(has_enough_data and drift_ratio > RECONCILE_SLO_MAX_DRIFT_RATIO)

    by_component: Dict[str, Dict[str, int]] = {}
    for component, outcome, count in component_rows:
        by_component.setdefault(component, {"ok": 0, "drift": 0})
        by_component[component][str(outcome)] = int(count)

    return {
        "window_minutes": effective_window,
        "total_events": total_events,
        "ok_events": ok_events,
        "drift_events": drift_events,
        "drift_ratio": round(drift_ratio, 6),
        "slo_max_drift_ratio": RECONCILE_SLO_MAX_DRIFT_RATIO,
        "slo_min_events": RECONCILE_SLO_MIN_EVENTS,
        "slo_has_enough_data": has_enough_data,
        "slo_violated": slo_violated,
        "alerts": {
            "reconcile_slo_violation": 1 if slo_violated else 0,
            "reconcile_drift_events_window": drift_events,
        },
        "last_reconcile_at": last_any[0].isoformat() if last_any and last_any[0] else None,
        "last_drift_at": last_drift[0].isoformat() if last_drift and last_drift[0] else None,
        "by_component": by_component,
    }


def _create_provision_session(request: ProvisionSessionPrepareRequest) -> str:
    session_id = str(uuid4())
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO edge_provisioning_sessions (session_id, status, request, validation, result)
                VALUES (%s, 'prepared', %s::jsonb, '{}'::jsonb, '{}'::jsonb)
                """,
                (session_id, json.dumps(request.model_dump())),
            )
    return session_id


def _load_provision_session(session_id: str) -> Dict[str, Any]:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT session_id, status, request, validation, result, error, created_at, updated_at
                FROM edge_provisioning_sessions
                WHERE session_id = %s
                """,
                (session_id,),
            )
            row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Provisioning session not found")

    return {
        "session_id": row[0],
        "status": row[1],
        "request": row[2],
        "validation": row[3],
        "result": row[4],
        "error": row[5],
        "created_at": row[6].isoformat() if row[6] else None,
        "updated_at": row[7].isoformat() if row[7] else None,
    }


def _update_provision_session(
    session_id: str,
    status: str,
    validation: dict | None = None,
    result: dict | None = None,
    error: str | None = None,
):
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE edge_provisioning_sessions
                SET status = %s,
                    validation = COALESCE(%s::jsonb, validation),
                    result = COALESCE(%s::jsonb, result),
                    error = %s,
                    updated_at = NOW()
                WHERE session_id = %s
                """,
                (
                    status,
                    json.dumps(validation) if validation is not None else None,
                    json.dumps(result) if result is not None else None,
                    error,
                    session_id,
                ),
            )


@app.on_event("startup")
def startup_event():
    _ensure_edge_audit_schema()
    _ensure_edge_control_plane_schema()


@app.get("/config")
def get_config(request: Request, x_edge_api_key: str | None = Header(default=None)):
    endpoint = "/config"
    actor = _authorize_scope("edge:config:read", x_edge_api_key, request, endpoint, "read_config")
    response = _load_config().model_dump()
    _log_edge_action(endpoint, "read_config", actor, "edge:config:read", "allowed", "success", _client_ip(request))
    return response


@app.put("/config")
def put_config(config: EdgeConfig, request: Request, x_edge_api_key: str | None = Header(default=None)):
    endpoint = "/config"
    actor = _authorize_scope("edge:config:write", x_edge_api_key, request, endpoint, "write_config")
    _save_config(config)
    _log_edge_action(
        endpoint,
        "write_config",
        actor,
        "edge:config:write",
        "allowed",
        "success",
        _client_ip(request),
        {"site_id": config.site_id, "site_name": config.site_name},
    )
    return {"updated": True, "config": config.model_dump()}


@app.post("/provision/device")
def provision_device(
    request: DeviceProvisionRequest,
    req_ctx: Request,
    x_edge_api_key: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    endpoint = "/provision/device"
    actor = _authorize_scope(
        "edge:provision",
        x_edge_api_key,
        req_ctx,
        endpoint,
        "provision_device",
        {"device_id": request.id, "house": request.house},
    )

    def _run_provision():
        _require_not_in_maintenance()
        desired = _load_desired_state()
        if not desired.provisioning_enabled:
            _log_edge_action(
                endpoint,
                "provision_device",
                actor,
                "edge:provision",
                "denied",
                "Provisioning disabled by desired state",
                _client_ip(req_ctx),
            )
            raise HTTPException(status_code=409, detail="Provisioning disabled by desired state")

        prepare_req = ProvisionSessionPrepareRequest(**request.model_dump(), installer_id="edge-direct")
        session_id = _create_provision_session(prepare_req)

        validate_result = _validate_session_internal(session_id)
        if not validate_result["valid"]:
            raise HTTPException(status_code=409, detail=validate_result["reason"])

        activation = _activate_session_internal(session_id)

        _log_edge_action(
            endpoint,
            "provision_device",
            actor,
            "edge:provision",
            "allowed",
            "success",
            _client_ip(req_ctx),
            {"device_id": request.id, "session_id": session_id},
        )
        return {"provisioned": True, "session_id": session_id, "response": activation}

    return _execute_idempotent(endpoint, idempotency_key, request.model_dump(), _run_provision)


@app.post("/lifecycle/reload-automation")
def reload_automation(request: Request, x_edge_api_key: str | None = Header(default=None)):
    endpoint = "/lifecycle/reload-automation"
    actor = _authorize_scope("edge:lifecycle:reload", x_edge_api_key, request, endpoint, "reload_automation")
    _require_not_in_maintenance()
    desired = _load_desired_state()
    if not desired.automation_enabled:
        raise HTTPException(status_code=409, detail="Automation disabled by desired state")

    token = _issue_token(
        subject="edge-controller-automation-admin",
        role="automation-admin",
        house="home01",
        scopes=["rules:reload"],
    )

    response = requests.post(
        f"{AUTOMATION_ENGINE_URL}/rules/reload",
        headers={"Authorization": f"Bearer {token}"},
        timeout=HTTP_TIMEOUT_SECONDS,
    )

    if response.status_code != 200:
        _log_edge_action(
            endpoint,
            "reload_automation",
            actor,
            "edge:lifecycle:reload",
            "denied",
            f"upstream_error:{response.status_code}",
            _client_ip(request),
        )
        raise HTTPException(status_code=502, detail=f"Automation reload failed: {response.text}")

    _log_edge_action(
        endpoint,
        "reload_automation",
        actor,
        "edge:lifecycle:reload",
        "allowed",
        "success",
        _client_ip(request),
    )
    return {"reloaded": True, "response": response.json()}


@app.post("/lifecycle/bridges/healthcheck")
def bridges_healthcheck(request: Request, x_edge_api_key: str | None = Header(default=None)):
    endpoint = "/lifecycle/bridges/healthcheck"
    actor = _authorize_scope("edge:lifecycle:bridges", x_edge_api_key, request, endpoint, "bridges_healthcheck")
    response = {
        "bridge_modbus": _service_health(BRIDGE_MODBUS_URL),
        "bridge_knx": _service_health(BRIDGE_KNX_URL),
        "bridge_bacnet": _service_health(BRIDGE_BACNET_URL),
    }
    _log_edge_action(
        endpoint,
        "bridges_healthcheck",
        actor,
        "edge:lifecycle:bridges",
        "allowed",
        "success",
        _client_ip(request),
    )
    return response


@app.post("/lifecycle/bridges/{bridge}/{command}")
def bridge_lifecycle_command(bridge: str, command: str, request: Request, x_edge_api_key: str | None = Header(default=None)):
    endpoint = "/lifecycle/bridges/{bridge}/{command}"
    actor = _authorize_scope(
        "edge:lifecycle:bridges",
        x_edge_api_key,
        request,
        endpoint,
        "bridge_lifecycle_command",
        {"bridge": bridge, "command": command},
    )
    _require_not_in_maintenance()

    try:
        result = _bridge_lifecycle_command(bridge, command)
    except HTTPException as exc:
        _log_edge_action(
            endpoint,
            "bridge_lifecycle_command",
            actor,
            "edge:lifecycle:bridges",
            "denied",
            str(exc.detail),
            _client_ip(request),
            {"bridge": bridge, "command": command},
        )
        raise
    except requests.RequestException as exc:
        _log_edge_action(
            endpoint,
            "bridge_lifecycle_command",
            actor,
            "edge:lifecycle:bridges",
            "denied",
            f"upstream_error:{exc}",
            _client_ip(request),
            {"bridge": bridge, "command": command},
        )
        raise HTTPException(status_code=502, detail=f"Bridge command request failed: {exc}")

    _log_edge_action(
        endpoint,
        "bridge_lifecycle_command",
        actor,
        "edge:lifecycle:bridges",
        "allowed",
        "success",
        _client_ip(request),
        {"bridge": bridge, "command": command},
    )
    return result


@app.get("/state/desired")
def get_desired_state(request: Request, x_edge_api_key: str | None = Header(default=None)):
    endpoint = "/state/desired"
    actor = _authorize_scope("edge:state:read", x_edge_api_key, request, endpoint, "get_desired_state")
    state = _load_desired_state().model_dump()
    _log_edge_action(endpoint, "get_desired_state", actor, "edge:state:read", "allowed", "success", _client_ip(request))
    return state


@app.put("/state/desired")
def put_desired_state(state: DesiredState, request: Request, x_edge_api_key: str | None = Header(default=None)):
    endpoint = "/state/desired"
    actor = _authorize_scope("edge:state:write", x_edge_api_key, request, endpoint, "put_desired_state")
    _save_desired_state(state, updated_by=actor)
    _log_edge_action(
        endpoint,
        "put_desired_state",
        actor,
        "edge:state:write",
        "allowed",
        "success",
        _client_ip(request),
        state.model_dump(),
    )
    return {"updated": True, "state": state.model_dump()}


@app.post("/reconcile/run")
def run_reconcile(request: Request, x_edge_api_key: str | None = Header(default=None)):
    endpoint = "/reconcile/run"
    actor = _authorize_scope("edge:state:reconcile", x_edge_api_key, request, endpoint, "run_reconcile")
    result = _reconcile_once()
    _log_edge_action(
        endpoint,
        "run_reconcile",
        actor,
        "edge:state:reconcile",
        "allowed",
        result["status"],
        _client_ip(request),
    )
    return result


@app.get("/reconcile/history")
def reconcile_history(request: Request, limit: int = 20, x_edge_api_key: str | None = Header(default=None)):
    endpoint = "/reconcile/history"
    actor = _authorize_scope("edge:state:read", x_edge_api_key, request, endpoint, "reconcile_history")
    effective_limit = max(1, min(limit, 200))
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT component, desired_state, actual_state, outcome, reason, metadata, created_at
                FROM edge_reconciliation_events
                ORDER BY event_id DESC
                LIMIT %s
                """,
                (effective_limit,),
            )
            rows = cur.fetchall()
    _log_edge_action(
        endpoint,
        "reconcile_history",
        actor,
        "edge:state:read",
        "allowed",
        "success",
        _client_ip(request),
        {"limit": effective_limit},
    )
    return {
        "items": [
            {
                "component": row[0],
                "desired_state": row[1],
                "actual_state": row[2],
                "outcome": row[3],
                "reason": row[4],
                "metadata": row[5],
                "created_at": row[6].isoformat() if row[6] else None,
            }
            for row in rows
        ]
    }


@app.get("/metrics/reconcile")
def reconcile_metrics(request: Request, window_minutes: int = RECONCILE_SLO_WINDOW_MINUTES, x_edge_api_key: str | None = Header(default=None)):
    endpoint = "/metrics/reconcile"
    actor = _authorize_scope("edge:state:read", x_edge_api_key, request, endpoint, "reconcile_metrics")
    metrics = _reconcile_slo_metrics(window_minutes)
    _log_edge_action(
        endpoint,
        "reconcile_metrics",
        actor,
        "edge:state:read",
        "allowed",
        "success",
        _client_ip(request),
        {"window_minutes": metrics["window_minutes"]},
    )
    return metrics


@app.get("/metrics/reconcile/prometheus")
def reconcile_metrics_prometheus(request: Request, window_minutes: int = RECONCILE_SLO_WINDOW_MINUTES, x_edge_api_key: str | None = Header(default=None)):
    endpoint = "/metrics/reconcile/prometheus"
    actor = _authorize_scope("edge:state:read", x_edge_api_key, request, endpoint, "reconcile_metrics_prometheus")
    metrics = _reconcile_slo_metrics(window_minutes)

    lines = [
        f"edge_reconcile_total_events {metrics['total_events']}",
        f"edge_reconcile_ok_events {metrics['ok_events']}",
        f"edge_reconcile_drift_events {metrics['drift_events']}",
        f"edge_reconcile_drift_ratio {metrics['drift_ratio']}",
        f"edge_reconcile_slo_violation {metrics['alerts']['reconcile_slo_violation']}",
        f"edge_reconcile_drift_events_window {metrics['alerts']['reconcile_drift_events_window']}",
    ]
    for component, counts in metrics["by_component"].items():
        lines.append(f"edge_reconcile_component_ok_events{{component=\"{component}\"}} {counts.get('ok', 0)}")
        lines.append(f"edge_reconcile_component_drift_events{{component=\"{component}\"}} {counts.get('drift', 0)}")

    _log_edge_action(
        endpoint,
        "reconcile_metrics_prometheus",
        actor,
        "edge:state:read",
        "allowed",
        "success",
        _client_ip(request),
        {"window_minutes": metrics["window_minutes"]},
    )
    return {"content_type": "text/plain", "metrics": "\n".join(lines) + "\n"}


def _validate_session_internal(session_id: str) -> Dict[str, Any]:
    session = _load_provision_session(session_id)
    request_data = session["request"]

    deps = dependency_health()
    if deps["status"] != "ok":
        validation = {"valid": False, "reason": "Dependencies degraded", "dependencies": deps}
        _update_provision_session(session_id, status="failed", validation=validation, error="Dependencies degraded")
        return validation

    try:
        existing = requests.get(
            f"{DEVICE_REGISTRY_URL}/devices/{request_data['id']}",
            timeout=HTTP_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        validation = {"valid": False, "reason": f"Registry lookup failed: {exc}"}
        _update_provision_session(session_id, status="failed", validation=validation, error="Registry lookup failed")
        return validation

    if existing.status_code == 200:
        validation = {"valid": False, "reason": "Device already exists"}
        _update_provision_session(session_id, status="failed", validation=validation, error="Device already exists")
        return validation
    if existing.status_code not in (404,):
        validation = {"valid": False, "reason": f"Unexpected registry response: {existing.status_code}"}
        _update_provision_session(session_id, status="failed", validation=validation, error="Unexpected registry response")
        return validation

    validation = {"valid": True, "reason": "ready"}
    _update_provision_session(session_id, status="validated", validation=validation)
    return validation


def _activate_session_internal(session_id: str) -> Dict[str, Any]:
    session = _load_provision_session(session_id)
    if session["status"] not in ("validated", "prepared"):
        raise HTTPException(status_code=409, detail=f"Session not activatable from status: {session['status']}")

    request_data = session["request"]
    token = _issue_token(
        subject="edge-controller-provisioner",
        role="provisioner",
        house=request_data["house"],
        scopes=["device:register"],
    )
    response = requests.post(
        f"{DEVICE_REGISTRY_URL}/devices/register",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        json={
            "id": request_data["id"],
            "house": request_data["house"],
            "type": request_data["type"],
            "protocol": request_data["protocol"],
            "capabilities": request_data.get("capabilities", []),
        },
        timeout=HTTP_TIMEOUT_SECONDS,
    )

    if response.status_code != 200:
        _update_provision_session(
            session_id,
            status="failed",
            result={"upstream_status": response.status_code, "body": response.text},
            error="Provisioning activation failed",
        )
        raise HTTPException(status_code=502, detail=f"Provisioning failed: {response.text}")

    result = response.json()
    _update_provision_session(session_id, status="activated", result=result)
    return result


@app.post("/provision/session/prepare")
def prepare_provision_session(
    request: ProvisionSessionPrepareRequest,
    req_ctx: Request,
    x_edge_api_key: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    endpoint = "/provision/session/prepare"
    actor = _authorize_scope(
        "edge:provision:session",
        x_edge_api_key,
        req_ctx,
        endpoint,
        "prepare_provision_session",
        {"device_id": request.id, "house": request.house},
    )
    def _run_prepare():
        _require_not_in_maintenance()
        desired = _load_desired_state()
        if not desired.provisioning_enabled:
            raise HTTPException(status_code=409, detail="Provisioning disabled by desired state")
        session_id = _create_provision_session(request)
        _log_edge_action(
            endpoint,
            "prepare_provision_session",
            actor,
            "edge:provision:session",
            "allowed",
            "prepared",
            _client_ip(req_ctx),
            {"session_id": session_id, "device_id": request.id},
        )
        return {"session_id": session_id, "status": "prepared"}

    return _execute_idempotent(endpoint, idempotency_key, request.model_dump(), _run_prepare)


@app.post("/provision/session/{session_id}/validate")
def validate_provision_session(
    session_id: str,
    req_ctx: Request,
    x_edge_api_key: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    endpoint = "/provision/session/validate"
    actor = _authorize_scope(
        "edge:provision:session",
        x_edge_api_key,
        req_ctx,
        endpoint,
        "validate_provision_session",
        {"session_id": session_id},
    )
    def _run_validate():
        _require_not_in_maintenance()
        result = _validate_session_internal(session_id)
        _log_edge_action(
            endpoint,
            "validate_provision_session",
            actor,
            "edge:provision:session",
            "allowed" if result["valid"] else "denied",
            result["reason"],
            _client_ip(req_ctx),
            {"session_id": session_id},
        )
        return result

    return _execute_idempotent(endpoint, idempotency_key, {"session_id": session_id}, _run_validate)


@app.post("/provision/session/{session_id}/activate")
def activate_provision_session(
    session_id: str,
    req_ctx: Request,
    x_edge_api_key: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    endpoint = "/provision/session/activate"
    actor = _authorize_scope(
        "edge:provision:session",
        x_edge_api_key,
        req_ctx,
        endpoint,
        "activate_provision_session",
        {"session_id": session_id},
    )
    def _run_activate():
        _require_not_in_maintenance()
        _validate_session_internal(session_id)
        result = _activate_session_internal(session_id)
        _log_edge_action(
            endpoint,
            "activate_provision_session",
            actor,
            "edge:provision:session",
            "allowed",
            "activated",
            _client_ip(req_ctx),
            {"session_id": session_id},
        )
        return {"activated": True, "result": result}

    return _execute_idempotent(endpoint, idempotency_key, {"session_id": session_id}, _run_activate)


@app.get("/provision/session/{session_id}")
def get_provision_session(session_id: str, request: Request, x_edge_api_key: str | None = Header(default=None)):
    endpoint = "/provision/session"
    actor = _authorize_scope("edge:provision:session", x_edge_api_key, request, endpoint, "get_provision_session")
    session = _load_provision_session(session_id)
    _log_edge_action(
        endpoint,
        "get_provision_session",
        actor,
        "edge:provision:session",
        "allowed",
        "success",
        _client_ip(request),
        {"session_id": session_id},
    )
    return session


@app.get("/maintenance/status")
def maintenance_status(request: Request, x_edge_api_key: str | None = Header(default=None)):
    endpoint = "/maintenance/status"
    actor = _authorize_scope("edge:maintenance:read", x_edge_api_key, request, endpoint, "maintenance_status")
    status = _maintenance_status()
    _log_edge_action(
        endpoint,
        "maintenance_status",
        actor,
        "edge:maintenance:read",
        "allowed",
        "success",
        _client_ip(request),
    )
    return status


@app.post("/maintenance/enable")
def maintenance_enable(
    body: MaintenanceRequest,
    request: Request,
    x_edge_api_key: str | None = Header(default=None),
):
    endpoint = "/maintenance/enable"
    actor = _authorize_scope("edge:maintenance:write", x_edge_api_key, request, endpoint, "maintenance_enable")
    _set_maintenance(enabled=True, reason=body.reason, actor=actor)
    _log_edge_action(
        endpoint,
        "maintenance_enable",
        actor,
        "edge:maintenance:write",
        "allowed",
        body.reason,
        _client_ip(request),
    )
    return {"enabled": True, "reason": body.reason}


@app.post("/maintenance/disable")
def maintenance_disable(request: Request, x_edge_api_key: str | None = Header(default=None)):
    endpoint = "/maintenance/disable"
    actor = _authorize_scope("edge:maintenance:write", x_edge_api_key, request, endpoint, "maintenance_disable")
    _set_maintenance(enabled=False, reason="none", actor=actor)
    _log_edge_action(
        endpoint,
        "maintenance_disable",
        actor,
        "edge:maintenance:write",
        "allowed",
        "disabled",
        _client_ip(request),
    )
    return {"enabled": False, "reason": "none"}


@app.get("/audit/recent")
def audit_recent(request: Request, limit: int = 20, x_edge_api_key: str | None = Header(default=None)):
    endpoint = "/audit/recent"
    actor = _authorize_scope("edge:audit:read", x_edge_api_key, request, endpoint, "audit_recent")
    effective_limit = max(1, min(limit, 200))

    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT endpoint, action, actor, scope, outcome, reason, client_ip, metadata, created_at
                FROM edge_controller_audit
                ORDER BY audit_id DESC
                LIMIT %s
                """,
                (effective_limit,),
            )
            rows = cur.fetchall()

    _log_edge_action(
        endpoint,
        "audit_recent",
        actor,
        "edge:audit:read",
        "allowed",
        "success",
        _client_ip(request),
        {"limit": effective_limit},
    )

    return {
        "items": [
            {
                "endpoint": row[0],
                "action": row[1],
                "actor": row[2],
                "scope": row[3],
                "outcome": row[4],
                "reason": row[5],
                "client_ip": row[6],
                "metadata": row[7],
                "created_at": row[8].isoformat() if row[8] else None,
            }
            for row in rows
        ]
    }
