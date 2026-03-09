from datetime import datetime, timezone
from typing import Dict, List, Optional

from device_sdk.core.models import DeviceDescriptor


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_announce_payload(device: DeviceDescriptor) -> Dict[str, object]:
    return {
        "event": "device_announce",
        "type": device.type,
        "protocol": device.protocol,
        "capabilities": device.capabilities,
        "timestamp": _utc_now_iso(),
    }


def build_event_payload(event: str, value: object, metadata: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    payload: Dict[str, object] = {
        "event": event,
        "value": value,
        "timestamp": _utc_now_iso(),
    }
    if metadata:
        payload["metadata"] = metadata
    return payload


def build_telemetry_payload(metrics: Dict[str, object], unit: Optional[str] = None) -> Dict[str, object]:
    payload: Dict[str, object] = {
        "metrics": metrics,
        "timestamp": _utc_now_iso(),
    }
    if unit:
        payload["unit"] = unit
    return payload


def build_status_payload(status: str, warnings: Optional[List[str]] = None) -> Dict[str, object]:
    payload: Dict[str, object] = {
        "status": status,
        "timestamp": _utc_now_iso(),
    }
    if warnings:
        payload["warnings"] = warnings
    return payload


def build_control_ack_payload(action: str, applied: bool, reason: str = "") -> Dict[str, object]:
    payload: Dict[str, object] = {
        "event": "control_ack",
        "action": action,
        "applied": applied,
        "timestamp": _utc_now_iso(),
    }
    if reason:
        payload["reason"] = reason
    return payload
